# yt-dlp API – Home Assistant Add-on

**Icon:** The add-on uses a custom icon (play + download arrow). To regenerate `logo.png` / `icon.png` from `icon.svg`, run `./build-icon.sh` in this directory (requires ImageMagick, rsvg-convert, or macOS).

This add-on runs the **yt-dlp REST API** inside Home Assistant OS, enabling you to download YouTube videos directly to your HA media library using the [ha-yt-dlp Lovelace card](../frontend/ha-card/).

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on store → ⋮ (overflow menu) → Repositories**.
2. Add the repository URL: `https://github.com/tarczyk/ha-yt-dlp`
3. Refresh the page. The **yt-dlp API** add-on will appear in the store.
4. Click **Install**, then **Start**.

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `port` | `5000` | TCP port the Flask API listens on inside the container |
| `media_subdir` | `youtube_downloads` | Subfolder under HA `/media` where downloads are saved (e.g. `youtube_downloads`, `videos`, `downloads`) |
| `cookies_file` | `youtube_cookies.txt` | Optional filename under HA `/config` with Netscape cookies for YouTube. Leave empty to disable. |

Example:

```yaml
port: 5000
media_subdir: youtube_downloads
cookies_file: youtube_cookies.txt
```

To save videos to a different folder in **Media Browser** (e.g. **My media → videos**), set `media_subdir: videos`. Only letters, numbers, underscores, hyphens and dots are allowed.

## Media storage

Downloaded files are written to `/media/<media_subdir>` inside the container, which is mapped to the HA `/media` share. They appear in **Media Browser → My media → &lt;media_subdir&gt;**.

## Download profiles

| Profile (`format`) | Result | When to use |
|---|---|---|
| `mp4` — MP4 (compatible video) | H.264 + AAC in `Title.mp4`, typically up to 1080p | Default. Plays on TVs and phones, including DLNA renderers. |
| `best_video` — Best video (original quality) | Best video + audio without re-encoding, e.g. AV1/VP9 + Opus in `Title [best].webm` (4K when the source has it). `Title [best].mp4` only if the source offers nothing but H.264. Never MKV. | Highest quality. The original codec may not play on every device; use MP4 if it doesn't. |
| `mp3` — MP3 (compatible audio) | Audio only in `Title.mp3` | Music or podcasts. |
| `best_audio` — Best audio (original quality) | The source's best audio stream without re-encoding: Opus in `Title [best].opus` on YouTube. | Highest audio quality. With an Opus source (YouTube), plays on a WiiM through HA's DLNA renderer. |

The `[best]` suffix keeps Best video and Best audio downloads from overwriting an MP4 or MP3 download of the same video.

**Best audio caveat:** when the source only offers AAC, the result is `Title [best].m4a`, still without re-encoding. HA hides `.m4a` files from the WiiM's DLNA renderer, so the file will not show up there. Use the MP3 profile as the compatible fallback (see ADR 0001).

If the source offers no audio-only stream, Best audio copies the audio track out of a video file instead (on YouTube typically AAC at a lower bitrate, again `Title [best].m4a`).

**Other sites:** Vorbis audio is kept as `Title [best].ogg`. A source whose audio cannot be copied into an audio-only file (e.g. E-AC-3) fails with "Requested format is not available" rather than being converted; use the MP3 profile for it.

## Using with the Lovelace card

Install the **yt-dlp Downloader Card** via HACS (add `https://github.com/tarczyk/ha-yt-dlp` as a custom Lovelace repository). Then add the card to your dashboard:

```yaml
type: custom:yt-dlp-card
api_url: http://homeassistant.local:5000
title: YouTube Downloader
max_tasks: 10
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Returns `{"status": "healthy"}` |
| `POST` | `/download_video` | Queue a download: `{"url": "https://..."}` |
| `GET` | `/tasks` | List all download tasks |
| `GET` | `/tasks/<id>` | Get status of a specific task |
| `GET` | `/files` | List downloaded files |
