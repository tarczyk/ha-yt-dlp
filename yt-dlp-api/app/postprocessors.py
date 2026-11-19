"""Custom yt-dlp post-processors."""
from __future__ import annotations

import os

from yt_dlp.postprocessor import FFmpegPostProcessor
from yt_dlp.utils import prepend_extension


class FastStartPP(FFmpegPostProcessor):
    """Move the MP4 index (moov atom) to the start of the file, without re-encoding.

    DLNA TVs reject MP4 files without it (ADR 0001). The yt-dlp merger can only do this for
    merged downloads, so this runs on the final file and also covers progressive downloads.
    Non-MP4 files are left untouched.
    """

    def run(self, information: dict):
        path = information["filepath"]
        if not path.lower().endswith(".mp4"):
            return [], information

        temp_path = prepend_extension(path, "faststart")
        self.run_ffmpeg(path, temp_path, ["-c", "copy", "-movflags", "+faststart"])
        os.replace(temp_path, path)
        return [], information
