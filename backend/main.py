# backend/main.py

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import yt_dlp
import uuid
import shutil
from pathlib import Path
import whisper
import time
import traceback
import redis
import json
from redis.exceptions import ConnectionError as RedisConnectionError

from schemas import (
    TranscriptionRequest,
    TranscriptionResponse,
    AnalysisResults,
)
from utils import (
    segments_to_srt_custom_lines,
    analyze_text_sentiment,
    analyze_text_pos_counts,
    analyze_text_word_frequency,
    analyze_text_topic,
)

# --- Constants ---
TEMP_DOWNLOAD_DIR = Path("./temp_audio")
WHISPER_MODEL_NAME = "base"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
CACHE_EXPIRATION_SECONDS = 3600  # 1 hour

# --- FastAPI App ---
app = FastAPI(
    title="Video Segment Transcriber API",
    description=(
        "API to download video segments, transcribe them (with SRT), "
        "perform analysis, and cache results."
    ),
    version="0.1.0",
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
    # add other allowed origins here
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Globals ---
whisper_model = None
redis_client = None

# --- Helper: Cleanup ---
def cleanup_temp_folder(folder_path: Path):
    if folder_path.exists() and folder_path.is_dir():
        print(f"Cleaning up temporary folder: {folder_path}")
        shutil.rmtree(folder_path)
    else:
        print(f"Temporary folder not found or is not a directory: {folder_path}")

# --- Dependency: Redis Client ---
async def get_redis_client():
    # Optionally raise if Redis is critical:
    # if not redis_client:
    #     raise HTTPException(status_code=503, detail="Cache service unavailable.")
    return redis_client

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    global whisper_model, redis_client

    # Create temp dir
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Temporary download directory created at {TEMP_DOWNLOAD_DIR.resolve()}")

    # Load Whisper model
    try:
        print(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
        t0 = time.time()
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        t1 = time.time()
        print(f"Whisper model loaded in {t1 - t0:.2f}s")
    except Exception as e:
        print(f"CRITICAL: Error loading Whisper model: {e}")
        print(traceback.format_exc())
        whisper_model = None

    # Connect to Redis
    try:
        print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        redis_client.ping()
        print("Redis connection established.")
    except RedisConnectionError as e:
        print(f"WARNING: Redis unavailable: {e}. Caching disabled.")
        redis_client = None
    except Exception as e:
        print(f"WARNING: Error connecting to Redis: {e}. Caching disabled.")
        redis_client = None

# --- Shutdown Event ---
@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup temp dir
    cleanup_temp_folder(TEMP_DOWNLOAD_DIR)
    print("Temporary download directory cleaned up.")

    # Close Redis
    global redis_client
    if redis_client:
        try:
            print("Closing Redis connection...")
            redis_client.close()
            print("Redis connection closed.")
        except Exception as e:
            print(f"Error closing Redis: {e}")

# --- Root Endpoint ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Video Transcriber API!"}

# --- Transcribe Endpoint ---
@app.post("/transcribe", response_model=TranscriptionResponse)
async def create_transcription_request(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    r_client: redis.Redis | None = Depends(get_redis_client),
):
    # Check cache
    cache_key = None
    if r_client:
        try:
            cache_key = (
                f"transcription:{request.video_url}:"
                f"{request.start_time}-{request.end_time}:"
                f"{request.generate_srt}:{request.analyze_sentiment}:"
                f"{request.analyze_pos}:{request.analyze_word_frequency}:"
                f"{request.analyze_topic}"
            )
            cached = r_client.get(cache_key)
            if cached:
                print(f"Cache HIT: {cache_key}")
                data = json.loads(cached)
                return TranscriptionResponse(**data)
            else:
                print(f"Cache MISS: {cache_key}")
        except RedisConnectionError as e:
            print(f"WARNING: Redis error on GET: {e}.")
            r_client = None
        except Exception as e:
            print(f"WARNING: Error during cache GET: {e}.")
            r_client = None

    # Ensure model loaded
    global whisper_model
    if whisper_model is None:
        raise HTTPException(status_code=503, detail="Model not loaded.")

    # Prepare directories
    request_id = str(uuid.uuid4())
    output_dir = TEMP_DOWNLOAD_DIR / request_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "audio.%(ext)s")

    # yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'postprocessor_args': [
            '-ss', request.start_time,
            '-to', request.end_time,
            '-copyts'
        ],
    }

    # Timing metrics
    t_start = time.time()
    download_t, transcribe_t, analysis_t = 0.0, 0.0, 0.0
    transcription_text = ""
    srt_output = None
    analysis_results = AnalysisResults()
    response_data: dict = {}

    try:
        # Download
        t0 = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            code = ydl.download([request.video_url])
            if code != 0:
                raise HTTPException(status_code=500, detail="Download failed.")
        t1 = time.time()
        download_t = t1 - t0

        files = list(output_dir.glob("audio.*"))
        if not files:
            raise HTTPException(status_code=500, detail="Audio file not found.")
        audio_path = files[0]
        print(f"Downloaded in {download_t:.2f}s → {audio_path}")

        # Transcribe
        t2 = time.time()
        result = whisper_model.transcribe(str(audio_path), fp16=False)
        t3 = time.time()
        transcribe_t = t3 - t2
        transcription_text = result.get("text", "").strip()
        print(f"Transcribed in {transcribe_t:.2f}s")

        # SRT
        if request.generate_srt:
            segments = result.get("segments")
            if segments:
                srt_output = segments_to_srt_custom_lines(segments)

        # Analysis
        if transcription_text:
            t4 = time.time()
            performed = False
            if request.analyze_sentiment:
                analysis_results.sentiment = analyze_text_sentiment(transcription_text)
                performed = True
            if request.analyze_pos:
                analysis_results.pos_counts = analyze_text_pos_counts(transcription_text)
                performed = True
            if request.analyze_word_frequency:
                analysis_results.word_frequency = analyze_text_word_frequency(transcription_text)
                performed = True
            if request.analyze_topic:
                analysis_results.topic = analyze_text_topic(transcription_text)
                performed = True
            if performed:
                t5 = time.time()
                analysis_t = t5 - t4
                print(f"Analysis in {analysis_t:.2f}s")

        # Build response
        t_end = time.time()
        total_t = t_end - t_start
        response_data = {
            "message": "Processing successful.",
            "transcription": transcription_text,
            "srt_transcription": srt_output,
            "analysis": (
                analysis_results
                if any([
                    request.analyze_sentiment,
                    request.analyze_pos,
                    request.analyze_word_frequency,
                    request.analyze_topic,
                ]) else None
            ),
            "original_url": request.video_url,
            "time_range": f"{request.start_time} - {request.end_time}",
            "download_seconds": round(download_t, 2),
            "transcription_seconds": round(transcribe_t, 2),
            "analysis_seconds": round(analysis_t, 2),
            "total_seconds": round(total_t, 2),
        }

        # Cache store
        if r_client and cache_key:
            try:
                r_client.setex(cache_key, CACHE_EXPIRATION_SECONDS, json.dumps(response_data))
                print(f"Cached: {cache_key}")
            except Exception as e:
                print(f"WARNING: Redis error on SETEX: {e}")

    except HTTPException:
        cleanup_temp_folder(output_dir)
        raise
    except Exception as e:
        cleanup_temp_folder(output_dir)
        print(f"CRITICAL: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Unexpected processing error.")

    # Schedule cleanup
    background_tasks.add_task(cleanup_temp_folder, output_dir)

    return TranscriptionResponse(**response_data)

# if __name__ == "__main__":
#    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
