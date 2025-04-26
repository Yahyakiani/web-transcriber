# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn
import yt_dlp
import os
import uuid
import shutil
from pathlib import Path
import whisper
import time
import traceback # For detailed error logging

# Import the schemas and utils
from schemas import TranscriptionRequest, TranscriptionResponse, AnalysisResults
# Import the new SRT function and analysis placeholders
from utils import (
    segments_to_srt_custom_lines,
    analyze_text_sentiment,
    analyze_text_pos_counts,
    analyze_text_word_frequency,
    analyze_text_topic
)

# --- Constants ---
TEMP_DOWNLOAD_DIR = Path("./temp_audio")
WHISPER_MODEL_NAME = "base"

# --- Global Variables ---
app = FastAPI(
    title="Video Segment Transcriber API",
    description="API to download video segments, transcribe them (with SRT), and perform analysis.",
    version="0.1.0",
)
whisper_model = None

# --- Helper Function for Cleanup ---
def cleanup_temp_folder(folder_path: Path):
    # ... (keep existing cleanup function) ...
    if folder_path.exists() and folder_path.is_dir():
        print(f"Cleaning up temporary folder: {folder_path}")
        shutil.rmtree(folder_path)
    else:
        print(f"Temporary folder not found or is not a directory: {folder_path}")


# --- Application Events (Startup/Shutdown) ---
@app.on_event("startup")
async def startup_event():
    """Create temp directory and load Whisper model on startup."""
    global whisper_model
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Temporary download directory created at {TEMP_DOWNLOAD_DIR.resolve()}")
    try:
        print(f"Loading Whisper model: {WHISPER_MODEL_NAME}...")
        model_load_start = time.time()
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        model_load_end = time.time()
        print(f"Whisper model '{WHISPER_MODEL_NAME}' loaded successfully in {model_load_end - model_load_start:.2f} seconds.")
        # TODO: Load NLP models (spaCy, etc.) here if needed for analysis on startup
    except Exception as e:
        print(f"CRITICAL: Error loading Whisper model: {e}")
        print(traceback.format_exc())
        whisper_model = None # Ensure it's None if loading failed


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up temp directory on shutdown."""
    cleanup_temp_folder(TEMP_DOWNLOAD_DIR)
    print("Temporary download directory cleaned up.")


# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Video Transcriber API!"}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def create_transcription_request(
    request: TranscriptionRequest, background_tasks: BackgroundTasks
):
    global whisper_model
    if whisper_model is None:
         raise HTTPException(status_code=503, detail="Transcription service unavailable: Model not loaded.")

    request_id = str(uuid.uuid4())
    output_dir = TEMP_DOWNLOAD_DIR / request_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"audio.%(ext)s")

    # --- Timing ---
    process_start_time = time.time()
    download_duration = 0.0
    transcription_duration = 0.0
    analysis_duration = 0.0
    # --- ---

    ydl_opts = { # ... (keep existing yt-dlp options) ...
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
            'postprocessor_args': {
                'ffmpeg': ['-ss', request.start_time, '-to', request.end_time, '-copyts']
            }
    }

    downloaded_file_path: Path | None = None
    transcription_text = ""
    srt_output = None
    analysis_results = AnalysisResults() # Initialize analysis results object

    try:
        print(f"Request {request_id}: Processing {request.video_url} [{request.start_time}-{request.end_time}]")

        # --- Download ---
        download_start_time = time.time()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([str(request.video_url)])
            if error_code != 0:
                # Maybe yt-dlp gave a more specific error? Check stderr or use verbose mode if needed.
                raise HTTPException(status_code=500, detail="yt-dlp download failed. Check URL and video availability.")
        download_end_time = time.time()
        download_duration = download_end_time - download_start_time

        potential_files = list(output_dir.glob("audio.*"))
        if not potential_files:
             raise HTTPException(status_code=500, detail="Downloaded audio file not found after processing.")
        downloaded_file_path = potential_files[0]
        print(f"Request {request_id}: Audio downloaded: {downloaded_file_path} (took {download_duration:.2f}s)")

        # --- Transcription ---
        transcribe_start_time = time.time()
        print(f"Request {request_id}: Starting transcription...")
        transcription_result_data = whisper_model.transcribe(
            str(downloaded_file_path),
            fp16=False # Keep False for CPU
        )
        transcribe_end_time = time.time()
        transcription_text = transcription_result_data.get("text", "").strip()
        transcription_duration = transcribe_end_time - transcribe_start_time
        print(f"Request {request_id}: Transcription complete (took {transcription_duration:.2f}s)")

        # --- SRT Generation (if requested) ---
        if request.generate_srt:
            segments = transcription_result_data.get("segments")
            if segments:
                print(f"Request {request_id}: Generating custom-line SRT format...")
                # Use the new function based on user's script
                srt_output = segments_to_srt_custom_lines(segments)
                print(f"Request {request_id}: SRT generation complete.")
            else:
                print(f"Request {request_id}: Segments data not found, cannot generate SRT.")

        # --- Analysis (if requested and text exists) ---
        if transcription_text:
            analysis_start_time = time.time()
            analysis_performed = False
            if request.analyze_sentiment:
                analysis_results.sentiment = analyze_text_sentiment(transcription_text)
                analysis_performed = True
            if request.analyze_pos:
                 analysis_results.pos_counts = analyze_text_pos_counts(transcription_text)
                 analysis_performed = True
            if request.analyze_word_frequency:
                 analysis_results.word_frequency = analyze_text_word_frequency(transcription_text)
                 analysis_performed = True
            if request.analyze_topic:
                 analysis_results.topic = analyze_text_topic(transcription_text)
                 analysis_performed = True

            if analysis_performed:
                analysis_end_time = time.time()
                analysis_duration = analysis_end_time - analysis_start_time
                print(f"Request {request_id}: Analysis performed (took {analysis_duration:.2f}s)")
        # --- ---

    except yt_dlp.utils.DownloadError as e:
        cleanup_temp_folder(output_dir)
        print(f"Request {request_id}: DownloadError: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download video/audio. Check URL/permissions. Error: {str(e)}")
    except Exception as e:
        cleanup_temp_folder(output_dir)
        print(f"Request {request_id}: CRITICAL Error during processing: {e}")
        print(traceback.format_exc()) # Log the full traceback for debugging server-side
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during processing.")

    # Schedule cleanup
    background_tasks.add_task(cleanup_temp_folder, output_dir)

    process_end_time = time.time()
    total_duration = process_end_time - process_start_time
    print(f"Request {request_id}: Total processing time: {total_duration:.2f}s")

    # Determine message based on success
    message = "Processing successful."
    if request.generate_srt and not srt_output and transcription_result_data.get("segments"):
        message = "Processing successful, but SRT generation failed (segments likely found but format error?)."
    elif request.generate_srt and not srt_output and not transcription_result_data.get("segments"):
         message = "Processing successful, but SRT generation failed (no segment data from Whisper)."

    return TranscriptionResponse(
        message=message,
        transcription=transcription_text,
        srt_transcription=srt_output,
        analysis=analysis_results if any([request.analyze_sentiment, request.analyze_pos, request.analyze_word_frequency, request.analyze_topic]) else None, # Only include analysis if requested
        original_url=request.video_url,
        time_range=f"{request.start_time} - {request.end_time}",
        # Include timing in response
        download_seconds=round(download_duration, 2),
        transcription_seconds=round(transcription_duration, 2),
        total_seconds=round(total_duration, 2)
    )

# if __name__ == "__main__":
#    # Consider setting reload=False if model loading takes too long during dev loops
#    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)