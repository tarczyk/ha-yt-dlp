"""Download Profile — single source of truth for format choices.

Each profile defines:
- ``api_value``: the string accepted in the ``format`` request field
- ``yt_dlp_opts``: a callable returning the yt-dlp option dict fragment

Every caller asks the profile instead of comparing format strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DownloadProfile:
    """One download profile (e.g. mp4, mp3)."""

    api_value: str
    # Returns yt-dlp option keys that differ between profiles.
    # Kept as a callable so each invocation gets an isolated options dict without shared mutable state.
    yt_dlp_opts: Callable[[], dict]


def _mp4_opts() -> dict:
    return {
        # Prefer MP4 for better compatibility (HA Media Browser, TVs, phones).
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
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
MP3 = DownloadProfile(api_value="mp3", yt_dlp_opts=_mp3_opts)

# Registered profiles keyed by API value.
PROFILES: dict[str, DownloadProfile] = {p.api_value: p for p in (MP4, MP3)}

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
