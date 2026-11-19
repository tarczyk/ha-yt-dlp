"""Tests for Download Profile — single source of truth for format choices."""
import pytest

from app.profiles import (
    ALLOWED_VALUES,
    DEFAULT_PROFILE,
    PROFILES,
    DownloadProfile,
    get_profile,
    BEST_VIDEO,
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

    def test_best_video_registered(self):
        assert "best_video" in PROFILES

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

    def test_best_video_lookup(self):
        profile = get_profile("best_video")
        assert profile is BEST_VIDEO
        assert profile.api_value == "best_video"

    def test_none_returns_default(self):
        """Omitting format → default profile (mp4)."""
        profile = get_profile(None)
        assert profile is DEFAULT_PROFILE
        assert profile.api_value == "mp4"

    def test_unknown_returns_none(self):
        assert get_profile("avi") is None
        assert get_profile("both") is None
        assert get_profile("") is None

    def test_non_string_returns_none(self):
        assert get_profile(["mp4"]) is None
        assert get_profile({"format": "mp4"}) is None
        assert get_profile(123) is None
        assert get_profile(True) is None


# ---------------------------------------------------------------------------
# Profile yt-dlp opts
# ---------------------------------------------------------------------------

class TestProfileOpts:
    def test_mp4_opts_format_string(self):
        opts = MP4.yt_dlp_opts()
        assert "format" in opts
        assert "avc" in opts["format"]  # H.264 preference
        assert opts["merge_output_format"] == "mp4"

    def test_mp3_opts_postprocessors(self):
        opts = MP3.yt_dlp_opts()
        assert opts["format"] == "bestaudio/best"
        assert any(
            pp.get("preferredcodec") == "mp3"
            for pp in opts.get("postprocessors", [])
        )

    def test_best_video_opts_format_string(self):
        opts = BEST_VIDEO.yt_dlp_opts()
        assert "format" in opts
        fmt = opts["format"]
        # Must prefer AV1 and VP9 (high quality)
        assert "av01" in fmt
        assert "vp9" in fmt
        # Must never produce MKV — merge_output_format must not include mkv
        merge = opts.get("merge_output_format", "")
        assert "mkv" not in merge

    def test_best_video_merge_output_excludes_mkv(self):
        """Container must be webm or mp4; MKV is forbidden (HA hides it)."""
        opts = BEST_VIDEO.yt_dlp_opts()
        merge = opts.get("merge_output_format", "")
        # Must mention webm (preferred for AV1/VP9+Opus)
        assert "webm" in merge
        assert "mkv" not in merge

    def test_best_video_format_prefers_av1_over_vp9(self):
        """AV1 selectors must appear before VP9 selectors in the format string."""
        fmt = BEST_VIDEO.yt_dlp_opts()["format"]
        assert fmt.index("av01") < fmt.index("vp9")

    def test_best_video_includes_h264_fallback(self):
        """Format string must include an avc/H.264 fallback for sources without AV1/VP9."""
        fmt = BEST_VIDEO.yt_dlp_opts()["format"]
        assert "avc" in fmt


# ---------------------------------------------------------------------------
# Filename suffix
# ---------------------------------------------------------------------------

class TestFilenameSuffix:
    def test_best_video_has_suffix(self):
        """Best Video profile must have a [best] suffix to avoid filename collisions."""
        assert BEST_VIDEO.filename_suffix == "[best]"

    def test_mp4_no_suffix(self):
        assert MP4.filename_suffix == ""

    def test_mp3_no_suffix(self):
        assert MP3.filename_suffix == ""


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
        assert data.get("allowed") == ALLOWED_VALUES
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
        assert data.get("allowed") == ALLOWED_VALUES

    def test_empty_string_format_returns_400(self, client):
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/watch?v=abc", "format": ""},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("allowed") == ALLOWED_VALUES

    def test_non_string_format_returns_400(self, client):
        """Non-string format types (list, dict, int) return 400 with allowed values."""
        for invalid_format in (["mp4"], {"type": "mp4"}, 123, True):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=abc", "format": invalid_format},
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert "error" in data
            assert data.get("allowed") == ALLOWED_VALUES

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

    def test_best_video_accepted(self, client):
        """best_video format must be accepted by the API endpoint."""
        from unittest.mock import patch
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
