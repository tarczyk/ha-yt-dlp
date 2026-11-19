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

## Download profiles

Pass `"format"` in the `POST /download_video` body to choose a profile.

| `format` value | Label | Description |
|----------------|-------|-------------|
| `mp4` *(default)* | MP4 (compatible video) | H.264 + AAC in MP4. Plays on the widest range of devices (TVs, phones, DLNA renderers). Typically limited to 1080 p on YouTube. |
| `best_video` | Best video (original quality) | Highest-quality video + audio the source offers, without re-encoding. AV1/VP9 + Opus streams are merged into WebM; H.264-only sources produce MP4. File is named `Title [best].webm` (or `.mp4`) to avoid collisions. **May not play on every device — use MP4 if it doesn't.** |
| `mp3` | MP3 (compatible audio) | Audio only, converted to 192 kbps MP3. |

### When to prefer MP4 over Best Video

Choose **MP4 (compatible video)** when:
- You need guaranteed playback on a Samsung TV, smart TV, or any DLNA renderer.
- Maximum compatibility matters more than picture quality.

Choose **Best video (original quality)** when:
- You want the highest available resolution (e.g. 4K AV1) and are willing to verify playback on your device.
- You are downloading to a PC or media player that supports modern codecs.
