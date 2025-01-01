# Use a specific Python 3.9 image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's caching mechanism
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . /app

# Set environment variable to ensure Python uses UTF-8 encoding
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python3", "main.py"]
