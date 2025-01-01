# Use Python 3.9 base image
FROM python:3.9-slim

# Install system dependencies including FFmpeg
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot source code into the container
COPY . /app/

# Make FFmpeg executable
RUN chmod +x ./ffmpeg/ffmpeg

# Set environment variables
ENV TOKEN=""
ENV HASH=""
ENV ID=""

# Start the application
CMD ["python3", "main.py"]
