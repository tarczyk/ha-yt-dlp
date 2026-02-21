# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install system dependencies: ffmpeg (for yt-dlp post-processing) and Node.js
# Node.js is used by yt-dlp as the JavaScript runtime (EJS) required for
# YouTube 2025+ signature decryption.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Default download directory; override via DOWNLOAD_DIR env variable.
RUN mkdir -p /media/youtube_downloads

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app.py"]
