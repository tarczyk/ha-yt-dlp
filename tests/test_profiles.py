"""Tests for Download Profile — single source of truth for format choices."""
import pytest

from app.profiles import (
    ALLOWED_VALUES,
    DEFAULT_PROFILE,
    PROFILES,
    DownloadProfile,
    get_profile,
    MP3,
    MP4,
)


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------

class TestProfileRegistry:
    def test_mp4_registered(self):
        assert "mp4" in PROFILES

    def test_mp3_registered(self):
        assert "mp3" in PROFILES

    def test_allowed_values_sorted(self):
        assert ALLOWED_VALUES == sorted(ALLOWED_VALUES)

    def test_allowed_values_match_profiles(self):
        assert set(ALLOWED_VALUES) == set(PROFILES)


# ---------------------------------------------------------------------------
# get_profile lookup
# ---------------------------------------------------------------------------

class TestGetProfile:
    def test_mp4_lookup(self):
        profile = get_profile("mp4")
        assert profile is MP4
        assert profile.api_value == "mp4"

    def test_mp3_lookup(self):
        profile = get_profile("mp3")
        assert profile is MP3
        assert profile.api_value == "mp3"

    def test_none_returns_default(self):
        """Omitting format → default profile (mp4)."""
        profile = get_profile(None)
        assert profile is DEFAULT_PROFILE
        assert profile.api_value == "mp4"

    def test_unknown_returns_none(self):
        assert get_profile("avi") is None
        assert get_profile("both") is None
        assert get_profile("") is None


# ---------------------------------------------------------------------------
# Profile yt-dlp opts
# ---------------------------------------------------------------------------

class TestProfileOpts:
    def test_mp4_opts_format_string(self):
        opts = MP4.yt_dlp_opts()
        assert "format" in opts
        assert "mp4" in opts["format"]
        assert opts["merge_output_format"] == "mp4"

    def test_mp3_opts_postprocessors(self):
        opts = MP3.yt_dlp_opts()
        assert opts["format"] == "bestaudio/best"
        assert any(
            pp.get("preferredcodec") == "mp3"
            for pp in opts.get("postprocessors", [])
        )

    def test_mp4_suffix(self):
        assert MP4.suffix == "mp4"

    def test_mp3_suffix(self):
        assert MP3.suffix == "mp3"


# ---------------------------------------------------------------------------
# Default profile
# ---------------------------------------------------------------------------

class TestDefaultProfile:
    def test_default_is_mp4(self):
        assert DEFAULT_PROFILE is MP4

    def test_default_api_value(self):
        assert DEFAULT_PROFILE.api_value == "mp4"


# ---------------------------------------------------------------------------
# API endpoint: unknown format → 400
# ---------------------------------------------------------------------------

class TestEndpointFormatValidation:
    """POST /download_video with unknown format returns 400 with allowed values."""

    def test_unknown_format_returns_400(self, client):
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/watch?v=abc", "format": "flv"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "flv" in data["error"]
        # Error message must list allowed values
        for val in ALLOWED_VALUES:
            assert val in data["error"]

    def test_both_format_returns_400(self, client):
        """The dead 'both' path is removed — it must be rejected."""
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/watch?v=abc", "format": "both"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "both" in data["error"]

    def test_empty_string_format_returns_400(self, client):
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/watch?v=abc", "format": ""},
        )
        assert resp.status_code == 400

    def test_omitted_format_defaults_to_mp4(self, client):
        """Omitting 'format' still means mp4."""
        from unittest.mock import patch
        import app.api as api_module

        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc"},
            )
        assert resp.status_code == 202
        task_id = resp.get_json()["task_id"]
        with api_module._tasks_lock:
            task = api_module._tasks[task_id]
        assert task["format"] == "mp4"

    def test_mp4_accepted(self, client):
        from unittest.mock import patch

        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc", "format": "mp4"},
            )
        assert resp.status_code == 202

    def test_mp3_accepted(self, client):
        from unittest.mock import patch

        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc", "format": "mp3"},
            )
        assert resp.status_code == 202
