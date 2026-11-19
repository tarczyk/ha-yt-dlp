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
    # Appended to the title, before the extension (e.g. " [best]"), so profiles never overwrite each other's files.
    filename_suffix: str = ""


def _mp4_opts() -> dict:
    return {
        # H.264 + AAC first: AV1/VP9 in MP4 are rejected by DLNA TVs (see ADR 0001).
        # The remaining branches are the previous selector, used only when the source has no H.264.
        "format": (
            "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[acodec^=mp4a][ext=m4a]"
            "/bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio"
            "/best[ext=mp4]"
            "/best"
        ),
        "merge_output_format": "mp4",
        # Put the MP4 index at the start of the file; TVs reject files without it.
        "postprocessor_args": {"merger": ["-movflags", "+faststart"]},
    }


def _best_video_opts() -> dict:
    return {
        # Original quality without re-encoding. AV1/VP9 + Opus merge into WebM, which DLNA TVs play (ADR 0001).
        # Fallback is H.264 + AAC (MP4) for sources that offer nothing else; never MKV.
        "format": (
            "bestvideo[vcodec~='^(av01|vp9|vp09)']+bestaudio[acodec=opus]"
            "/bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]"
            "/best[ext=webm]"
            "/best[ext=mp4]"
        ),
        # Ordered preference: first container that can hold the selected streams. MKV is not listed.
        "merge_output_format": "webm/mp4",
        "postprocessor_args": {"merger": ["-movflags", "+faststart"]},
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
BEST_VIDEO = DownloadProfile(api_value="best_video", yt_dlp_opts=_best_video_opts, filename_suffix=" [best]")

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
