# Use python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies 
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files 
COPY ./app /app/app

# Copy firebase-key if exists (Mount it via docker-compose usually, but copy if present)
# Using a glob to avoid error if file not present during build
COPY firebase-key.json* /app/

# Set env 
ENV PYTHONPATH=/app
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-key.json

# Expose port 
EXPOSE 8000

# Run uvicorn (Shell form allows environment variables like $PORT)
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
