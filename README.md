# yt-dlp-ha-docker

🐳 Docker Compose yt-dlp API for Home Assistant with EJS (Node.js) support.  
Downloads to `/media/youtube_downloads` • Compatible with the `youtube_downloader` integration.

## Features

- **Flask REST API** – `POST /download_video` and `GET /health`
- **yt-dlp** with Node.js as the JavaScript runtime (EJS) for YouTube 2025+ compatibility
- **ffmpeg** for post-processing (merging video/audio streams)
- **Volume** mounted at `/media/youtube_downloads` – visible in HA Media Browser
- **Multi-arch** image: `linux/amd64` and `linux/arm64` (aarch64 / Raspberry Pi)
- **Healthcheck** + `restart: unless-stopped` for reliable operation

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/tarczyk/yt-dlp-ha-docker.git
cd yt-dlp-ha-docker
```

### 2. Configure environment

Copy `.env` and adjust as needed:

```bash
cp .env .env.local   # optional – docker-compose reads .env automatically
```

| Variable | Default | Description |
|---|---|---|
| `API_PORT` | `8080` | Host port for the Flask API |
| `DOWNLOAD_DIR` | `/media/youtube_downloads` | Host path where videos are saved |
| `YT_DLP_EXTRA_ARGS` | *(empty)* | Extra flags passed to `yt-dlp` |

### 3. Build and start

```bash
docker compose up -d --build
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8080/health

# Download a video
curl -X POST http://localhost:8080/download_video \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## API Reference

### `GET /health`

Returns `200 OK` when the service is running.

```json
{"status": "ok"}
```

### `POST /download_video`

Downloads a video to `DOWNLOAD_DIR`.

**Request body**

```json
{"url": "https://www.youtube.com/watch?v=..."}
```

**Success response** (`200`)

```json
{"status": "downloaded", "output": "...yt-dlp stdout..."}
```

**Error response** (`400` / `500` / `504`)

```json
{"error": "...description..."}
```

## Home Assistant Integration

After the container is running, Home Assistant can trigger downloads via a REST command:

```yaml
# configuration.yaml
rest_command:
  download_youtube_video:
    url: "http://<your-docker-host>:8080/download_video"
    method: POST
    headers:
      Content-Type: application/json
    payload: '{"url": "{{ url }}"}'
```

## Multi-Arch Build

To push a multi-architecture image to a registry:

```bash
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t youruser/yt-dlp-ha-api:latest \
  --push .
```

## License

MIT
