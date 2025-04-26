# backend/utils.py
import datetime
import math # Needed for ceil

def format_timestamp(seconds: float, always_include_hours: bool = False) -> str:
    """Formats seconds into HH:MM:SS,ms"""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000

    minutes = milliseconds // 60_000
    milliseconds %= 60_000

    seconds = milliseconds // 1_000
    milliseconds %= 1_000

    # Our format uses comma before milliseconds
    if not always_include_hours and hours == 0:
         # Your script used HH:MM:SS,ms even if hours was 0, let's match timedelta's behaviour
         # return f"{minutes:02d}:{seconds:02d},{milliseconds:03d}" # Original format without hours
        pass # Fall through to HH:MM:SS,ms format

    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def segments_to_srt_custom_lines(segments: list) -> str:
    """
    Converts whisper segments into SRT format string, attempting to break
    segments into smaller lines with estimated timestamps.

    NOTE: Timestamps for lines shorter than original segments are ESTIMATED
          based on word count and may not be perfectly accurate.
    """
    srt_content = ""
    segment_line_idx = 1 # Overall index for SRT lines, starting from 1
    min_words_per_line = 2  # Minimum number of words per line
    target_words_per_line = 3 # Target number of words per line

    for segment in segments:
        words = segment["text"].strip().split() # Get words and remove leading/trailing space
        if not words: # Skip empty segments
            continue

        # Use segment start/end provided by Whisper
        segment_start_time = segment['start']
        segment_end_time = segment['end']
        segment_duration = segment_end_time - segment_start_time

        # Estimate duration per word IF segment duration is positive
        # Avoid division by zero if segment duration is 0 or words list is empty
        word_duration = (segment_duration / len(words)) if segment_duration > 0 and words else 0

        current_word_index = 0
        while current_word_index < len(words):
            # Determine the end index for the current line
            # If remaining words are more than min, aim for target, else take all remaining
            if len(words) - current_word_index > min_words_per_line:
                line_end_word_index = min(current_word_index + target_words_per_line, len(words))
            else:
                line_end_word_index = len(words)

            # Extract words for the current line
            line_words = words[current_word_index:line_end_word_index]

            # Estimate start and end time for this specific line
            # Add a tiny epsilon to end time calculation to avoid exact overlap issues if word_duration is 0
            epsilon = 1e-6
            line_start_seconds = segment_start_time + (current_word_index * word_duration)
            # Ensure end time doesn't exceed segment end time
            line_end_seconds = min(segment_start_time + (line_end_word_index * word_duration) + epsilon, segment_end_time)

            # Format timestamps using the utility function
            start_str = format_timestamp(line_start_seconds)
            end_str = format_timestamp(line_end_seconds)

            # Format the SRT block
            line_text = " ".join(line_words)
            srt_content += f"{segment_line_idx}\n"
            srt_content += f"{start_str} --> {end_str}\n"
            srt_content += f"{line_text}\n\n"

            segment_line_idx += 1
            current_word_index = line_end_word_index # Move to the next set of words

    return srt_content.strip() # Remove trailing newline

# --- Placeholder for future analysis functions ---
def analyze_text_sentiment(text: str) -> dict:
    """Placeholder: Analyzes sentiment (positive/negative/neutral)."""
    # TODO: Implement using VADER, TextBlob, or Transformers
    print("[Analysis] Sentiment analysis requested (Not Implemented)")
    return {"sentiment_label": "N/A", "sentiment_score": 0.0}

def analyze_text_pos_counts(text: str) -> dict:
    """Placeholder: Counts parts of speech (nouns, verbs, etc.)."""
    # TODO: Implement using spaCy or NLTK
    print("[Analysis] POS counting requested (Not Implemented)")
    return {"pos_counts": {}}

def analyze_text_word_frequency(text: str) -> dict:
    """Placeholder: Counts frequency of each word."""
    # TODO: Implement using collections.Counter after normalization
    print("[Analysis] Word frequency requested (Not Implemented)")
    return {"word_frequency": {}}

def analyze_text_topic(text: str) -> dict:
    """Placeholder: Determines the general topic."""
    # TODO: Implement using keyword extraction, topic modeling, or classification
    print("[Analysis] Topic analysis requested (Not Implemented)")
    return {"topic": "N/A"}
# --- End Placeholders ---