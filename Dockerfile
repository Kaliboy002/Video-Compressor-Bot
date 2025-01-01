# Use a lightweight Python image
FROM python:3.9-slim

# Install FFmpeg and other dependencies
RUN apt-get update && \
    apt-get install -y wget && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xvf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg*/ffmpeg ffmpeg*/ffprobe /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port
EXPOSE 80

# Run the bot
CMD ["python", "main.py"]
