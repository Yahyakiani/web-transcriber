# backend/Dockerfile

# --- Base Stage ---
# Use an official Python runtime as a parent image
# Choose a version compatible with your code and dependencies (e.g., 3.10 or 3.11)
# Using slim-bullseye for a smaller image size
FROM python:3.10-slim-bullseye as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents python from writing .pyc files
ENV PYTHONUNBUFFERED 1      # Prevents python from buffering stdout/stderr

# Set working directory
WORKDIR /app

# Install system dependencies required by some Python packages (like Whisper or yt-dlp/ffmpeg)
# Update package lists, install ffmpeg and potentially rust (if whisper build needs it), clean up lists
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates build-essential && \
    # Optional: Install Rust if needed for Whisper compilation (often needed)
    curl https://sh.rustup.rs -sSf | sh -s -- --default-toolchain stable -y && \
    export PATH="/root/.cargo/bin:${PATH}" && \
    # Verify rust installation (optional)
    # rustc --version && \
    # Clean up apt cache to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add Rust binaries to the path for subsequent steps
ENV PATH="/root/.cargo/bin:${PATH}"

# --- Builder Stage (for dependencies) ---
FROM base as builder

# Install build dependencies like gcc if needed by specific packages (build-essential from base should cover most)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file first to leverage Docker cache
COPY requirements.txt .

# Create and activate a virtual environment (optional but good practice)
# RUN python -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
# Using --no-cache-dir can reduce image size slightly
# Whisper might take a while to build/install
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
# Pull from the base image again to keep the final image leaner
FROM base as final

# Copy installed dependencies from builder stage (if using venv)
# COPY --from=builder /opt/venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# If not using venv, copy installed packages directly (simpler for this case)
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Ensure ffmpeg and rust binaries are available if needed at runtime (copied from base)
# Ensure Whisper models directory exists if needed (Whisper downloads models on first run)
# RUN mkdir -p /root/.cache/whisper

# Copy application code
COPY . /app

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# Use uvicorn directly. --host 0.0.0.0 makes it accessible from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]