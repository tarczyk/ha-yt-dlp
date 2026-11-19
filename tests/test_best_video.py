"""Tests for the Best Video download profile (api value: best_video).

Covers:
- format selector in the profile registry
- container choice (WebM for AV1/VP9, MP4 for H.264-only, never MKV)
- filename suffix ([best]) to prevent collisions
- API endpoint acceptance
- yt_dlp_manager outtmpl uses the suffix
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from app.profiles import BEST_VIDEO, ALLOWED_VALUES, MP4, get_profile
from app.yt_dlp_manager import download_video


# ---------------------------------------------------------------------------
# Profile selector
# ---------------------------------------------------------------------------

class TestBestVideoProfileSelector:
    def test_api_value(self):
        assert BEST_VIDEO.api_value == "best_video"

    def test_lookup_by_api_value(self):
        assert get_profile("best_video") is BEST_VIDEO

    def test_in_allowed_values(self):
        assert "best_video" in ALLOWED_VALUES

    def test_allowed_values_includes_all_three(self):
        assert set(ALLOWED_VALUES) >= {"mp4", "best_video", "mp3"}


# ---------------------------------------------------------------------------
# Container choice — format string
# ---------------------------------------------------------------------------

class TestBestVideoContainer:
    """The format string must steer yt-dlp toward WebM for AV1/VP9 and never MKV."""

    def _opts(self):
        return BEST_VIDEO.yt_dlp_opts()

    def test_prefers_av1_opus_webm(self):
        fmt = self._opts()["format"]
        # First selector should target AV1 video + Opus audio
        first = fmt.split("/")[0]
        assert "av01" in first
        assert "opus" in first

    def test_prefers_vp9_before_h264(self):
        fmt = self._opts()["format"]
        assert fmt.index("vp9") < fmt.index("avc"), (
            "VP9 selectors must appear before H.264/avc selectors"
        )

    def test_includes_h264_fallback(self):
        """Sources that only offer H.264 must still produce a file (MP4)."""
        fmt = self._opts()["format"]
        assert "avc" in fmt

    def test_merge_output_contains_webm(self):
        """WebM must be listed in merge_output_format for AV1/VP9+Opus merging."""
        merge = self._opts()["merge_output_format"]
        assert "webm" in merge

    def test_merge_output_never_mkv(self):
        """MKV must never appear — HA hides MKV from DLNA renderers (ADR 0001)."""
        merge = self._opts()["merge_output_format"]
        assert "mkv" not in merge

    def test_merge_output_includes_mp4_fallback(self):
        """MP4 must be a fallback for H.264-only sources."""
        merge = self._opts()["merge_output_format"]
        assert "mp4" in merge

    def test_webm_before_mp4_in_merge(self):
        """WebM must be preferred over MP4 in merge_output_format."""
        merge = self._opts()["merge_output_format"]
        assert merge.index("webm") < merge.index("mp4")


# ---------------------------------------------------------------------------
# Filename suffix — prevents collision with MP4 of the same video
# ---------------------------------------------------------------------------

class TestBestVideoFilenameSuffix:
    def test_suffix_is_best(self):
        assert BEST_VIDEO.filename_suffix == "[best]"

    def test_outtmpl_contains_suffix(self, tmp_path):
        """download_video must insert [best] before the extension in outtmpl."""
        fake_info = {"title": "My Video", "ext": "webm"}
        with patch("app.yt_dlp_manager.yt_dlp.YoutubeDL") as MockYDL:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.extract_info.return_value = fake_info
            MockYDL.return_value = instance

            download_video(
                "https://www.youtube.com/watch?v=test",
                output_dir=str(tmp_path),
                profile=BEST_VIDEO,
            )

        # Inspect the ydl_opts passed to YoutubeDL
        call_kwargs = MockYDL.call_args[0][0]  # first positional arg is the opts dict
        outtmpl = call_kwargs["outtmpl"]
        assert "[best]" in outtmpl, f"Expected '[best]' in outtmpl, got: {outtmpl}"

    def test_mp4_outtmpl_has_no_suffix(self, tmp_path):
        """MP4 profile must NOT add any suffix to the filename."""
        fake_info = {"title": "My Video", "ext": "mp4"}
        with patch("app.yt_dlp_manager.yt_dlp.YoutubeDL") as MockYDL:
            instance = MagicMock()
            instance.__enter__ = MagicMock(return_value=instance)
            instance.__exit__ = MagicMock(return_value=False)
            instance.extract_info.return_value = fake_info
            MockYDL.return_value = instance

            download_video(
                "https://www.youtube.com/watch?v=test",
                output_dir=str(tmp_path),
                profile=MP4,
            )

        call_kwargs = MockYDL.call_args[0][0]
        outtmpl = call_kwargs["outtmpl"]
        assert "[best]" not in outtmpl, f"MP4 outtmpl must not contain '[best]', got: {outtmpl}"


# ---------------------------------------------------------------------------
# API endpoint integration
# ---------------------------------------------------------------------------

class TestBestVideoApiEndpoint:
    def test_best_video_format_accepted(self, client):
        """POST /download_video with format=best_video must return 202."""
        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc", "format": "best_video"},
            )
        assert resp.status_code == 202

    def test_best_video_task_records_format(self, client):
        """The created task must record format='best_video'."""
        import app.api as api_module

        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc", "format": "best_video"},
            )
        assert resp.status_code == 202
        task_id = resp.get_json()["task_id"]
        with api_module._tasks_lock:
            task = api_module._tasks[task_id]
        assert task["format"] == "best_video"

    def test_best_video_in_error_message_for_bad_format(self, client):
        """Error response for unknown format must list best_video in allowed values."""
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/watch?v=abc", "format": "flv"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "best_video" in data.get("allowed", [])
        assert "best_video" in data.get("error", "")
