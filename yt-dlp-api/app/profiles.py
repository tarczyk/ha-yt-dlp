"""Download Profile — single source of truth for format choices.

Each profile defines:
- ``api_value``: the string accepted in the ``format`` request field
- ``yt_dlp_opts``: a callable returning the yt-dlp option dict fragment
- ``filename_suffix``: optional suffix inserted before the extension (e.g. ``[best]``)

Every caller asks the profile instead of comparing format strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class DownloadProfile:
    """One download profile (e.g. mp4, best_video, mp3)."""

    api_value: str
    # Returns yt-dlp option keys that differ between profiles.
    # Kept as a callable so each invocation gets an isolated options dict without shared mutable state.
    yt_dlp_opts: Callable[[], dict]
    # Optional suffix added before the file extension to prevent collisions (e.g. ``[best]``).
    filename_suffix: str = field(default="")


def _mp4_opts() -> dict:
    return {
        # Prefer H.264 + AAC in MP4 for the widest DLNA compatibility (ADR 0001).
        # faststart moves the moov atom to the front so Samsung TVs accept the file.
        "format": (
            "bestvideo[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo[vcodec^=avc]+bestaudio"
            "/best[ext=mp4]/best"
        ),
        "merge_output_format": "mp4",
        "postprocessor_args": {"ffmpeg": ["-movflags", "+faststart"]},
    }


def _best_video_opts() -> dict:
    # Per ADR 0001: highest-quality video + audio merged into WebM (AV1/VP9 + Opus).
    # MP4 is the fallback only when the source offers nothing but H.264.
    # MKV is never produced — HA hides it for DLNA renderers.
    return {
        "format": (
            "bestvideo[vcodec^=av01]+bestaudio[acodec=opus]"
            "/bestvideo[vcodec^=vp9]+bestaudio[acodec=opus]"
            "/bestvideo[vcodec^=av01]+bestaudio"
            "/bestvideo[vcodec^=vp9]+bestaudio"
            "/bestvideo[vcodec^=avc][ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio"
            "/best"
        ),
        # Merge AV1/VP9 streams into WebM; H.264-only sources produce MP4.
        # mp4 is listed after webm so yt-dlp prefers WebM for AV1/VP9.
        "merge_output_format": "webm/mp4",
    }


def _mp3_opts() -> dict:
    return {
        # Download best audio and convert to MP3.
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }


MP4 = DownloadProfile(api_value="mp4", yt_dlp_opts=_mp4_opts)
BEST_VIDEO = DownloadProfile(
    api_value="best_video",
    yt_dlp_opts=_best_video_opts,
    filename_suffix="[best]",
)
MP3 = DownloadProfile(api_value="mp3", yt_dlp_opts=_mp3_opts)

# Registered profiles keyed by API value.
# Order: MP4, BEST_VIDEO, MP3 — matches the UI display order.
PROFILES: dict[str, DownloadProfile] = {p.api_value: p for p in (MP4, BEST_VIDEO, MP3)}

# Convenience: sorted list of allowed API values (for error messages).
ALLOWED_VALUES: list[str] = sorted(PROFILES)

# Default profile when ``format`` is omitted.
DEFAULT_PROFILE: DownloadProfile = MP4


def get_profile(api_value: str | None) -> DownloadProfile | None:
    """Return the profile for *api_value*, or ``None`` if unknown.

    Passing ``None`` returns the default profile (mp4).
    """
    if api_value is None:
        return DEFAULT_PROFILE
    if not isinstance(api_value, str):
        return None
    return PROFILES.get(api_value)
