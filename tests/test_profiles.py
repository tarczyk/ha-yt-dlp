"""Tests for Download Profile — single source of truth for format choices."""
import shutil
import subprocess

import pytest

from app.profiles import (
    ALLOWED_VALUES,
    DEFAULT_PROFILE,
    BEST_VIDEO,
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
        assert "mp4" in opts["format"]
        assert opts["merge_output_format"] == "mp4"

    def test_mp4_requests_faststart_for_every_mp4(self):
        """Faststart is a profile property applied by a post-processor, so progressive downloads get it too."""
        assert MP4.faststart is True

    def test_mp3_opts_postprocessors(self):
        opts = MP3.yt_dlp_opts()
        assert opts["format"] == "bestaudio/best"
        assert any(
            pp.get("preferredcodec") == "mp3"
            for pp in opts.get("postprocessors", [])
        )


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


class TestBestVideo:
    def test_registered_and_allowed(self):
        from app.profiles import ALLOWED_VALUES, BEST_VIDEO, get_profile

        assert get_profile("best_video") is BEST_VIDEO
        assert "best_video" in ALLOWED_VALUES

    def test_prefers_modern_codecs_with_opus(self):
        from app.profiles import BEST_VIDEO

        first = BEST_VIDEO.yt_dlp_opts()["format"].split("/")[0]
        assert "av01" in first and "vp9" in first
        assert "acodec=opus" in first

    def test_h264_only_fallback_uses_aac(self):
        from app.profiles import BEST_VIDEO

        second = BEST_VIDEO.yt_dlp_opts()["format"].split("/")[1]
        assert "vcodec^=avc1" in second and "acodec^=mp4a" in second

    def test_container_is_webm_then_mp4_never_mkv(self):
        from app.profiles import BEST_VIDEO

        assert BEST_VIDEO.yt_dlp_opts()["merge_output_format"] == "webm/mp4"

    def test_requests_faststart_for_mp4_output(self):
        from app.profiles import BEST_VIDEO

        assert BEST_VIDEO.faststart is True

    def test_filename_suffix_distinguishes_from_mp4(self):
        from app.profiles import BEST_VIDEO, MP3, MP4

        assert BEST_VIDEO.filename_suffix == " [best]"
        assert MP4.filename_suffix == ""
        assert MP3.filename_suffix == ""

    def test_outtmpl_includes_suffix(self):
        from unittest.mock import MagicMock, patch

        from app.profiles import BEST_VIDEO, MP4
        from app.yt_dlp_manager import download_video

        for profile, expected in ((BEST_VIDEO, "/d/%(title)s [best].%(ext)s"), (MP4, "/d/%(title)s.%(ext)s")):
            with patch("app.yt_dlp_manager.yt_dlp.YoutubeDL") as ydl:
                ydl.return_value.__enter__.return_value = MagicMock(extract_info=MagicMock(return_value={}))
                download_video("https://x", output_dir="/d", profile=profile)
            assert ydl.call_args[0][0]["outtmpl"] == expected


# ---------------------------------------------------------------------------
# MP4 format selection — run through yt-dlp's real selector
# ---------------------------------------------------------------------------

def _fmt(format_id, ext, vcodec, acodec, height=0):
    return {
        "format_id": format_id, "ext": ext, "vcodec": vcodec, "acodec": acodec,
        "height": height, "url": "https://example.invalid/" + format_id, "protocol": "https",
    }


def _select_mp4(formats):
    """Format ids yt-dlp would download for the MP4 profile (formats ordered worst → best)."""
    import yt_dlp

    ydl = yt_dlp.YoutubeDL({"quiet": True})
    selector = ydl.build_format_selector(MP4.yt_dlp_opts()["format"])
    chosen = list(selector({"formats": formats, "incomplete_formats": False}))
    assert len(chosen) == 1
    return [f["format_id"] for f in chosen[0].get("requested_formats", [chosen[0]])]


_OPUS = _fmt("a_opus", "webm", "none", "opus")
_AAC = _fmt("a_aac", "m4a", "none", "mp4a.40.2")
_H264 = _fmt("v_h264", "mp4", "avc1.640028", "none", 1080)
_VP9 = _fmt("v_vp9", "webm", "vp09.00.50.08", "none", 2160)
_AV1 = _fmt("v_av1", "mp4", "av01.0.12M.08", "none", 2160)


class TestMp4FormatSelection:
    def test_h264_aac_wins_when_av1_and_vp9_are_offered(self):
        assert _select_mp4([_OPUS, _AAC, _H264, _VP9, _AV1]) == ["v_h264", "a_aac"]

    def test_h264_aac_wins_regardless_of_format_order(self):
        assert _select_mp4([_AV1, _VP9, _H264, _AAC, _OPUS]) == ["v_h264", "a_aac"]

    def test_progressive_h264_aac_wins_over_av1_when_streams_cannot_be_merged(self):
        progressive = _fmt("p_h264", "mp4", "avc1.42001E", "mp4a.40.2", 360)
        assert _select_mp4([_OPUS, progressive, _AV1]) == ["p_h264"]

    def test_fallback_used_when_source_has_no_h264(self):
        # No H.264 anywhere: best MP4-compatible streams (AV1 in MP4 + AAC) rather than failure.
        assert _select_mp4([_OPUS, _AAC, _VP9, _AV1]) == ["v_av1", "a_aac"]

    def test_fallback_still_downloads_when_nothing_is_mp4_compatible(self):
        assert _select_mp4([_OPUS, _VP9]) == ["v_vp9", "a_opus"]


def _select_best(formats):
    """(format ids, output ext) yt-dlp would produce for the Best Video profile."""
    import yt_dlp

    opts = BEST_VIDEO.yt_dlp_opts()
    ydl = yt_dlp.YoutubeDL({"quiet": True, "merge_output_format": opts["merge_output_format"]})
    chosen = list(ydl.build_format_selector(opts["format"])({"formats": formats, "incomplete_formats": False}))
    assert len(chosen) == 1
    ids = [f["format_id"] for f in chosen[0].get("requested_formats", [chosen[0]])]
    return ids, chosen[0]["ext"]


class TestBestVideoFormatSelection:
    def test_av1_and_opus_merge_into_webm(self):
        assert _select_best([_OPUS, _AAC, _H264, _AV1]) == (["v_av1", "a_opus"], "webm")

    def test_vp9_and_opus_merge_into_webm(self):
        assert _select_best([_OPUS, _AAC, _H264, _VP9]) == (["v_vp9", "a_opus"], "webm")

    def test_h264_only_source_merges_into_mp4(self):
        assert _select_best([_AAC, _H264]) == (["v_h264", "a_aac"], "mp4")

    def test_av1_without_opus_falls_back_to_h264_not_av1_in_mp4(self):
        assert _select_best([_AAC, _H264, _AV1]) == (["v_h264", "a_aac"], "mp4")

    def test_progressive_mp4_preferred_over_progressive_webm(self):
        webm = _fmt("p_webm", "webm", "vp8", "vorbis", 360)
        mp4 = _fmt("p_mp4", "mp4", "avc1.64001F", "mp4a.40.2", 720)
        assert _select_best([webm, mp4]) == (["p_mp4"], "mp4")

    def test_streams_without_codec_info_still_download(self):
        progressive = _fmt("p_flv", "flv", None, None, 480)
        assert _select_best([progressive]) == (["p_flv"], "flv")

    def test_unusual_codec_pair_never_produces_mkv(self):
        from yt_dlp.utils import get_compatible_ext

        ext = get_compatible_ext(
            vcodecs=["vp09.00.50.08"], acodecs=["mp4a.40.2"], vexts=["webm"], aexts=["m4a"],
            preferences=BEST_VIDEO.yt_dlp_opts()["merge_output_format"].split("/"),
        )
        assert ext != "mkv"


# ---------------------------------------------------------------------------
# Faststart post-processor
# ---------------------------------------------------------------------------

def _first_atoms(path):
    """Top-level MP4 atom names in file order."""
    atoms = []
    with open(path, "rb") as fh:
        while True:
            header = fh.read(8)
            if len(header) < 8:
                return atoms
            size = int.from_bytes(header[:4], "big")
            atoms.append(header[4:8].decode("latin-1"))
            if size == 1:
                size = int.from_bytes(fh.read(8), "big")
                fh.seek(size - 16, 1)
            else:
                fh.seek(size - 8, 1)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
class TestFaststartPostProcessor:
    def _make_mp4(self, path, faststart):
        flags = ["-movflags", "+faststart"] if faststart else []
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=1:s=64x64:r=10",
             "-c:v", "libx264", *flags, str(path)],
            check=True,
        )

    def test_moves_index_to_start_of_progressive_mp4(self, tmp_path):
        import yt_dlp
        from app.postprocessors import FastStartPP

        path = tmp_path / "clip.mp4"
        self._make_mp4(path, faststart=False)
        assert _first_atoms(path).index("moov") > _first_atoms(path).index("mdat")

        FastStartPP(yt_dlp.YoutubeDL({"quiet": True})).run({"filepath": str(path)})

        assert _first_atoms(path).index("moov") < _first_atoms(path).index("mdat")

    def test_leaves_non_mp4_untouched(self, tmp_path):
        import yt_dlp
        from app.postprocessors import FastStartPP

        path = tmp_path / "clip.webm"
        path.write_bytes(b"not a real webm")

        FastStartPP(yt_dlp.YoutubeDL({"quiet": True})).run({"filepath": str(path)})

        assert path.read_bytes() == b"not a real webm"
