# backend/main.py
from fastapi import FastAPI
import uvicorn # Keep uvicorn import for potential programmatic start

app = FastAPI(
    title="Video Segment Transcriber API",
    description="API to download video segments and transcribe them.",
    version="0.1.0",
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Video Transcriber API!"}

# Placeholder for the transcription endpoint
@app.post("/transcribe")
async def create_transcription_request():
    # TODO: Implement logic
    return {"message": "Transcription endpoint placeholder"}

# To run locally (optional, usually run via uvicorn command)
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)