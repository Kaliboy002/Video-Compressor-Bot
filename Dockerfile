# Use the official Python image as the base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (FFmpeg and necessary libraries)
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from the requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the bot's source code into the container
COPY . /app/

# Make FFmpeg executable
RUN chmod +x ./ffmpeg/ffmpeg

# Set the environment variables (you can also use Railway's environment variables)
ENV TOKEN=""
ENV HASH=""
ENV ID=""

# Start the application
CMD ["python3", "main.py"]
