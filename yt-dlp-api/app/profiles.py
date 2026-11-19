"""Download Profile — single source of truth for format choices.

Each profile defines:
- ``api_value``: the string accepted in the ``format`` request field
- ``yt_dlp_opts``: a callable returning the yt-dlp option dict fragment
- ``filename_suffix``: text appended to the title, before the extension
- ``faststart``: whether the final MP4 gets its index moved to the start

Every caller asks the profile instead of comparing format strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DownloadProfile:
    """One download profile (e.g. mp4, best_video, mp3)."""

    api_value: str
    # Returns yt-dlp option keys that differ between profiles.
    # Kept as a callable so each invocation gets an isolated options dict without shared mutable state.
    yt_dlp_opts: Callable[[], dict]
    # Appended to the title, before the extension (e.g. " [best]"), so profiles never overwrite each other's files.
    filename_suffix: str = ""
    # Rewrite the final MP4 with the index at the start (see ``FastStartPP``). Needed by DLNA TVs.
    faststart: bool = False


def _mp4_opts() -> dict:
    return {
        # H.264 + AAC first: AV1/VP9 in MP4 are rejected by DLNA TVs (see ADR 0001).
        # Branches 1-2 cover every H.264 + AAC source (merged or progressive). Branches 3+ are the
        # previous selector and are reached only when the source has no H.264 + AAC at all.
        "format": (
            "bestvideo[vcodec^=avc1][ext=mp4]+bestaudio[acodec^=mp4a][ext=m4a]"
            "/best[vcodec^=avc1][acodec^=mp4a][ext=mp4]"
            "/bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo+bestaudio"
            "/best[ext=mp4]"
            "/best"
        ),
        "merge_output_format": "mp4",
    }


def _best_video_opts() -> dict:
    return {
        # Original quality without re-encoding. AV1/VP9 + Opus merge into WebM, which DLNA TVs play (ADR 0001).
        # AV1/VP9 without Opus deliberately falls to H.264 + AAC: the only container left for it is MP4,
        # which the TV rejects for AV1/VP9. Progressive files come last; prefer MP4, never fail outright.
        "format": (
            "bestvideo[vcodec~='^(av01|vp9|vp09)']+bestaudio[acodec=opus]"
            "/bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]"
            "/best[ext=mp4]"
            "/best[ext=webm]"
            "/best"
        ),
        # Ordered preference: first container that can hold the selected streams. Without mkv in the
        # list yt-dlp never picks MKV.
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


MP4 = DownloadProfile(api_value="mp4", yt_dlp_opts=_mp4_opts, faststart=True)
BEST_VIDEO = DownloadProfile(
    api_value="best_video", yt_dlp_opts=_best_video_opts, filename_suffix=" [best]", faststart=True,
)
MP3 = DownloadProfile(api_value="mp3", yt_dlp_opts=_mp3_opts)

# Registered profiles keyed by API value.
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
