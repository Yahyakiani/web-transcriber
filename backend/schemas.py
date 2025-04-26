# backend/schemas.py
from pydantic import BaseModel, HttpUrl, validator, Field
import re

# Basic regex for HH:MM:SS or MM:SS format (can be refined)
TIME_FORMAT_REGEX = re.compile(r'^(\d{1,2}:)?\d{1,2}:\d{2}$')

class TranscriptionRequest(BaseModel):
    video_url: HttpUrl # Pydantic validates if it's a valid URL
    start_time: str = Field(..., pattern=r'^(\d{1,2}:)?\d{1,2}:\d{2}$') # Example: "1:05", "00:30", "1:15:30"
    end_time: str = Field(..., pattern=r'^(\d{1,2}:)?\d{1,2}:\d{2}$')

    # Optional: Add custom validation to ensure end_time > start_time if needed
    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values, **kwargs):
        if 'start_time' in values and v <= values['start_time']: # Basic string comparison, might need parsing for accuracy
             raise ValueError('end_time must be after start_time')
        return v

class TranscriptionResponse(BaseModel):
    message: str
    transcription: str | None = None # Or specify SRT format later
    original_url: HttpUrl
    time_range: str