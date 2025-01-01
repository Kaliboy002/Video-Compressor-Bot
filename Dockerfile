# Use official Python image as the base image
FROM python:3.9

# Set working directory
WORKDIR /app

# Install FFmpeg dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install -r requirements.txt

# Copy the rest of the bot's files into the container
COPY . /app

# Set the environment variable for the FFmpeg binary
ENV PATH="/app/ffmpeg:${PATH}"

# Ensure FFmpeg has executable permissions (if it's bundled with your app)
RUN chmod +x /app/ffmpeg/ffmpeg

# Run the bot
CMD ["python3", "main.py"]
