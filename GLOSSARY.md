# ha-yt-dlp

Downloads online videos into the Home Assistant media library so they can be played on household devices.

## Language

**Download Profile**:
The user's choice of what to keep from a video: a compatible MP4, the best available video, an MP3, or the best available audio.
_Avoid_: Format, quality, preset

**MP4 profile**:
Video with sound in an MP4 file, chosen for playback on as many devices as possible rather than for maximum quality.
_Avoid_: Video, default format

**Best Video profile**:
The highest-quality video with sound the source offers, in whatever codec that is, limited only by the configured maximum resolution.
_Avoid_: Original, 4K, max quality

**MP3 profile**:
Audio only, converted to MP3 for players that accept nothing else.
_Avoid_: Audio, music

**Best Audio profile**:
The source's best audio stream kept exactly as published, without re-encoding.
_Avoid_: Lossless, FLAC, original audio
