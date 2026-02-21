import logging
import sys
from typing import Callable

import yt_dlp


class DownloadCancelledError(Exception):
    """Raised when the user cancels the download via API."""


def _yt_dlp_logger():
    """Logger that writes yt-dlp messages to stderr so they appear in addon logs."""
    log = logging.getLogger("yt-dlp")
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)
    return log


def download_video(
    url: str,
    output_dir: str = "/config/media",
    timeout: int = 1800,
    stop_check: Callable[[], bool] | None = None,
) -> dict:
    """Download a video using yt-dlp and return info dict.
    If stop_check is provided and returns True during download, raises DownloadCancelledError.
    """
    def progress_hook(d: dict) -> None:
        if stop_check and stop_check():
            raise DownloadCancelledError("Cancelled by user")

    ydl_opts = {
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "quiet": True,
        "logger": _yt_dlp_logger(),
        "socket_timeout": timeout,
        "progress_hooks": [progress_hook],
        # When URL has both v= and list= (e.g. watch?v=XXX&list=RD...), download only this video.
        "noplaylist": True,
        # Prefer MP4 for better compatibility (HA Media Browser, TVs, phones).
        # Without this, yt-dlp defaults to "best" and YouTube often serves WebM (VP9).
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        # Keep yt-dlp's cache in /tmp so it works even when the container runs
        # as a non-root user without a writable home directory.
        "cachedir": "/tmp/yt-dlp",
        # Explicit JS runtime for EJS (n-sig challenge). Image has Node and Deno.
        "js_runtimes": {"node": {}},
        # Fetch EJS scripts from GitHub if bundled yt-dlp-ejs is missing/outdated (n-sig solving).
        "remote_components": ["ejs:github"],
        # Prefer web clients to avoid YouTube's DRM-on-tv experiment (issue #12563).
        # When tv client is used first, some accounts get only DRM formats → "This video is DRM protected".
        # default + web_safari + web_embedded avoid tv; EJS (yt-dlp-ejs + Node) handles n-sig if needed.
        "extractor_args": {
            "youtube": {
                "player_client": ["default", "web_safari", "web_embedded"],
            },
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
    return info or {}


def extract_info(url: str) -> dict:
    """Extract video info without downloading."""
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info or {}
