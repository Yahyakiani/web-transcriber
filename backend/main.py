# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn
import yt_dlp
import os
import uuid
import shutil
from pathlib import Path
import whisper  # Import the whisper library

from schemas import TranscriptionRequest, TranscriptionResponse

# --- Constants ---
TEMP_DOWNLOAD_DIR = Path("./temp_audio")
WHISPER_MODEL_NAME = "base"  # Choose model size: tiny, base, small, medium, large
                            # Larger models are more accurate but slower and require more resources.
                            # Start with "base" or "small".

# --- Global Variables ---
app = FastAPI(
    title="Video Segment Transcriber API",
    description="API to download video segments and transcribe them.",
    version="0.1.0",
)
whisper_model = None  # Global variable to hold the loaded model

# --- Helper Function for Cleanup ---
def cleanup_temp_folder(folder_path: Path):
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
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
        print(f"Whisper model '{WHISPER_MODEL_NAME}' loaded successfully.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        # Decide if the app should fail to start if model loading fails.
        # For now, we'll allow it to start but transcription will fail.
        whisper_model = None

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up temp directory on shutdown."""
    cleanup_temp_folder(TEMP_DOWNLOAD_DIR)
    print("Temporary download directory cleaned up.")
    # Note: No explicit cleanup needed for the Whisper model object itself usually.

# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Video Transcriber API!"}

@app.post("/transcribe", response_model=TranscriptionResponse)
async def create_transcription_request(
    request: TranscriptionRequest, background_tasks: BackgroundTasks
):
    """
    Downloads a video segment's audio and transcribes it using Whisper.
    """
    global whisper_model  # Access the globally loaded model

    if whisper_model is None:
         raise HTTPException(status_code=503, detail="Transcription service unavailable: Model not loaded.")

    request_id = str(uuid.uuid4())
    output_dir = TEMP_DOWNLOAD_DIR / request_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"audio.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',  # Download best audio quality
        'outtmpl': output_template,  # Output filename template
        'quiet': True,               # Let's make yt-dlp quieter now
        'no_warnings': True,
        'noplaylist': True,          # Don't download playlists
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio
            'preferredcodec': 'wav',      # Convert to WAV (often good for Whisper)
            'preferredquality': '192',    # Audio quality
        }],
        'postprocessor_args': {
            'ffmpeg': ['-ss', request.start_time, '-to', request.end_time, '-copyts']
        }
    }

    downloaded_file_path: Path | None = None
    try:
        print(f"Processing request {request_id}: Downloading {request.video_url} [{request.start_time}-{request.end_time}]")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([str(request.video_url)])
            if error_code != 0:
                raise HTTPException(status_code=500, detail="yt-dlp download failed.")

        potential_files = list(output_dir.glob("audio.*"))
        if not potential_files:
             raise HTTPException(status_code=500, detail="Downloaded audio file not found after processing.")
        downloaded_file_path = potential_files[0]
        print(f"Request {request_id}: Audio segment downloaded: {downloaded_file_path}")

        # --- Transcription Step ---
        print(f"Request {request_id}: Starting transcription...")
        # Note: This runs synchronously in the main thread.
        # For longer audio/bigger models, this will block the server.
        # We will address this later if needed (e.g., using run_in_executor).
        transcription_result_data = whisper_model.transcribe(
            str(downloaded_file_path),
            fp16=False  # Set to True if you have a GPU and CUDA installed for faster processing
                       # Keep False for CPU-based processing (likely in free tier)
        )
        transcription_text = transcription_result_data.get("text", "").strip()
        print(f"Request {request_id}: Transcription complete.")
        # --- ---

    except yt_dlp.utils.DownloadError as e:
        cleanup_temp_folder(output_dir)  # Cleanup on specific error
        print(f"Request {request_id}: DownloadError: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download video/audio. Error: {str(e)}")
    except Exception as e:
        cleanup_temp_folder(output_dir)  # Cleanup on general error
        print(f"Request {request_id}: Error during processing: {e}")
        # Add more specific error handling for transcription if needed
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {str(e)}")

    # Schedule cleanup *after* successful processing and transcription
    background_tasks.add_task(cleanup_temp_folder, output_dir)

    return TranscriptionResponse(
        message="Transcription successful.",
        transcription=transcription_text,
        original_url=request.video_url,
        time_range=f"{request.start_time} - {request.end_time}"
    )

# To run locally (if needed)
# if __name__ == "__main__":
#    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)  # Note: reload might cause model to reload often
