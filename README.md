# yt-dlp-ha-docker

🐳 Docker Compose yt-dlp API for Home Assistant. Downloads to `/media/youtube_downloads` • Compatible with the `youtube_downloader` integration.

![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)
![Python](https://img.shields.io/badge/python-3.12--alpine-blue?logo=python)
![Security: no-new-privileges](https://img.shields.io/badge/security-no--new--privileges-green)
![Security: read-only fs](https://img.shields.io/badge/security-read--only%20fs-green)
![Security: non-root user](https://img.shields.io/badge/security-non--root%20user-green)
![Security: capabilities dropped](https://img.shields.io/badge/security-caps%20dropped-green)
![License](https://img.shields.io/github/license/tarczyk/yt-dlp-ha-docker)

## Security hardening

| Feature | Value |
|---|---|
| Base image | `python:3.12-alpine` |
| Run as user | `appuser` (UID 1000, non-root) |
| Read-only filesystem | ✅ (`read_only: true`) |
| No new privileges | ✅ (`no-new-privileges:true`) |
| Capabilities | All dropped; `CHOWN` and `SETGID` added back |
| Tmpfs | `/tmp` mounted as tmpfs |
| Port binding | `127.0.0.1:5000:5000` (localhost only) |

## Quick start

```bash
docker compose up -d
```

## API

### `POST /download`

Download a video/audio file.

```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

### `GET /health`

Returns `{"status": "ok"}` when the service is running.
