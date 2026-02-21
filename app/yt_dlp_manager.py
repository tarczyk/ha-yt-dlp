import yt_dlp


def download_video(url: str, output_dir: str = "/config/media", timeout: int = 1800) -> dict:
    """Download a video using yt-dlp and return info dict."""
    ydl_opts = {
        "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
        "quiet": True,
        "socket_timeout": timeout,
        # remote_components downloads JavaScript from GitHub to support yt-dlp EJS extractors.
        # Only enable if you trust the component source; this introduces an external dependency.
        "remote_components": "ejs:github",
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
