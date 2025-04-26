# backend/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
import uvicorn
import yt_dlp
import os
import uuid # To create unique filenames/directories
import shutil # For cleaning up temp directories
from pathlib import Path

# Import the schemas
from schemas import TranscriptionRequest, TranscriptionResponse

# --- Constants ---
TEMP_DOWNLOAD_DIR = Path("./temp_audio")

app = FastAPI(
    title="Video Segment Transcriber API",
    description="API to download video segments and transcribe them.",
    version="0.1.0",
)

# --- Helper Function for Cleanup ---
def cleanup_temp_folder(folder_path: Path):
    if folder_path.exists() and folder_path.is_dir():
        print(f"Cleaning up temporary folder: {folder_path}")
        shutil.rmtree(folder_path)
    else:
        print(f"Temporary folder not found or is not a directory: {folder_path}")


# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    """Create temp directory on startup."""
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Temporary download directory created at {TEMP_DOWNLOAD_DIR.resolve()}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up temp directory on shutdown."""
    cleanup_temp_folder(TEMP_DOWNLOAD_DIR)
    print("Temporary download directory cleaned up.")


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Video Transcriber API!"}


@app.post("/transcribe", response_model=TranscriptionResponse)
async def create_transcription_request(
    request: TranscriptionRequest, background_tasks: BackgroundTasks
):
    """
    Downloads a video segment's audio and prepares for transcription.
    (Transcription logic will be added in the next step)
    """
    request_id = str(uuid.uuid4())
    output_dir = TEMP_DOWNLOAD_DIR / request_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define filename structure within the unique dir
    # Using %(ext)s ensures the correct extension is used
    output_template = str(output_dir / f"audio.%(ext)s")

    # Time range format for yt-dlp's download_ranges
    # NOTE: yt-dlp expects seconds or HH:MM:SS. Need to parse our input.
    # We'll implement a simple parser, or rely on ffmpeg post-processing later.
    # For now, let's use ffmpeg post-processing which is more robust.

    # yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best', # Download best audio quality
        'outtmpl': output_template, # Output filename template
        'quiet': False, # Set to True for less verbose output
        'no_warnings': True,
        'noplaylist': True, # Don't download playlists
        'postprocessors': [{
            'key': 'FFmpegExtractAudio', # Extract audio
            'preferredcodec': 'wav',      # Convert to WAV (often good for Whisper)
            'preferredquality': '192',    # Audio quality
        }],
        # We will use FFmpeg post-processor args for precise cutting
        'postprocessor_args': {
            'ffmpeg': [
                '-ss', request.start_time, # Start time
                '-to', request.end_time,   # End time
                '-copyts' # Copy timestamps to avoid reset issues
             ]
        }
        # Using postprocessor_args for cutting is generally more reliable than --download-sections
        # especially if the source needs transcoding anyway.
    }

    downloaded_file_path = None
    try:
        print(f"Attempting download for {request.video_url} [{request.start_time}-{request.end_time}]")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download([str(request.video_url)])
            if error_code != 0:
                raise HTTPException(status_code=500, detail="yt-dlp download failed.")

        # Find the downloaded file (yt-dlp might change extension)
        # It should be the only file matching 'audio.*' in the output dir
        potential_files = list(output_dir.glob("audio.*"))
        if not potential_files:
             raise HTTPException(status_code=500, detail="Downloaded audio file not found.")
        downloaded_file_path = potential_files[0] # Take the first match
        print(f"Audio segment downloaded successfully: {downloaded_file_path}")

    except yt_dlp.utils.DownloadError as e:
        # Cleanup before raising exception
        cleanup_temp_folder(output_dir)
        print(f"DownloadError: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download video/audio. Invalid URL or video format? Error: {str(e)}")
    except Exception as e:
        # Cleanup before raising exception
        cleanup_temp_folder(output_dir)
        print(f"Unexpected Error: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during download: {str(e)}")

    # --- Placeholder for Transcription Step ---
    # TODO: Call Whisper model here with downloaded_file_path
    transcription_result = f"Transcription for {downloaded_file_path.name} goes here."
    # --- ---

    # Schedule the cleanup task to run after the response is sent
    background_tasks.add_task(cleanup_temp_folder, output_dir)


    return TranscriptionResponse(
        message="Audio segment processed. Transcription placeholder.",
        transcription=transcription_result, # Replace with actual transcription
        original_url=request.video_url,
        time_range=f"{request.start_time} - {request.end_time}"
    )


# To run locally (if needed, though 'uvicorn main:app --reload' is better)
# if __name__ == "__main__":
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)