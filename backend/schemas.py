# backend/schemas.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any # Import Dict and Any for analysis results

# Keep TIME_FORMAT_REGEX if you still use Field(..., pattern=...) validation
# import re
# TIME_FORMAT_REGEX = re.compile(r'^(\d{1,2}:)?\d{1,2}:\d{2}$')

class TranscriptionRequest(BaseModel):
    video_url: HttpUrl
    start_time: str # Consider adding validation back or using a dedicated time parsing library
    end_time: str   # Consider adding validation back or using a dedicated time parsing library
    generate_srt: bool = Field(default=True, description="Generate SRT format output using custom line breaking.")

    # Flags for future analysis (default to False)
    analyze_sentiment: bool = Field(default=False, description="Perform sentiment analysis on the transcript.")
    analyze_pos: bool = Field(default=False, description="Perform Part-of-Speech counting.")
    analyze_word_frequency: bool = Field(default=False, description="Calculate word frequency.")
    analyze_topic: bool = Field(default=False, description="Attempt topic detection.")


class AnalysisResults(BaseModel):
    """Structure to hold all potential analysis results."""
    sentiment: Dict[str, Any] | None = None
    pos_counts: Dict[str, Any] | None = None
    word_frequency: Dict[str, Any] | None = None
    topic: Dict[str, Any] | None = None


class TranscriptionResponse(BaseModel):
    message: str
    transcription: str | None = None # Plain text transcription
    srt_transcription: str | None = None # SRT format transcription (custom lines)
    analysis: AnalysisResults | None = None # Add the analysis results structure
    original_url: HttpUrl
    time_range: str
    # Optional: Timing info
    download_seconds: float | None = None
    transcription_seconds: float | None = None
    total_seconds: float | None = None