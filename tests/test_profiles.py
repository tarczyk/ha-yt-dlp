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


def _select_mp4(formats, max_height=None):
    """Format ids yt-dlp would download for the MP4 profile (formats ordered worst → best)."""
    import yt_dlp

    ydl = yt_dlp.YoutubeDL({"quiet": True})
    selector = ydl.build_format_selector(MP4.yt_dlp_opts(max_height=max_height)["format"])
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


def _select_best(formats, max_height=None):
    """(format ids, output ext) yt-dlp would produce for the Best Video profile."""
    import yt_dlp

    opts = BEST_VIDEO.yt_dlp_opts(max_height=max_height)
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


_AV1_8K = _fmt("v_av1_8k", "mp4", "av01.0.17M.08", "none", 4320)
_VP9_4K = _fmt("v_vp9_4k", "webm", "vp09.00.51.08", "none", 2160)


class TestBestVideoMaxHeight:
    def test_8k_is_downloaded_without_a_limit(self):
        assert _select_best([_OPUS, _VP9_4K, _AV1_8K]) == (["v_av1_8k", "a_opus"], "webm")

    def test_limit_caps_8k_source_at_2160p(self):
        assert _select_best([_OPUS, _VP9_4K, _AV1_8K], max_height=2160) == (["v_vp9_4k", "a_opus"], "webm")

    def test_limit_applies_to_h264_fallback(self):
        h264_1440 = _fmt("v_h264_1440", "mp4", "avc1.640032", "none", 1440)
        assert _select_best([_AAC, _H264, h264_1440], max_height=1080) == (["v_h264", "a_aac"], "mp4")

    def test_limit_applies_to_progressive_fallback(self):
        p_720 = _fmt("p_720", "mp4", "avc1.64001F", "mp4a.40.2", 720)
        p_1080 = _fmt("p_1080", "mp4", "avc1.640028", "mp4a.40.2", 1080)
        assert _select_best([p_720, p_1080], max_height=720) == (["p_720"], "mp4")

    def test_nothing_within_limit_selects_nothing_rather_than_exceeding_it(self):
        import yt_dlp

        selector = yt_dlp.YoutubeDL({"quiet": True}).build_format_selector(
            BEST_VIDEO.yt_dlp_opts(max_height=2160)["format"],
        )
        assert list(selector({"formats": [_OPUS, _AV1_8K], "incomplete_formats": False})) == []


class TestMp4MaxHeight:
    _H264_1440 = _fmt("v_h264_1440", "mp4", "avc1.640032", "none", 1440)

    def test_highest_h264_is_downloaded_without_a_limit(self):
        assert _select_mp4([_AAC, _H264, self._H264_1440]) == ["v_h264_1440", "a_aac"]

    def test_limit_caps_h264_resolution(self):
        assert _select_mp4([_AAC, _H264, self._H264_1440], max_height=1080) == ["v_h264", "a_aac"]

    def test_limit_applies_to_fallback_without_h264(self):
        av1_1080 = _fmt("v_av1_1080", "mp4", "av01.0.08M.08", "none", 1080)
        assert _select_mp4([_AAC, av1_1080, _AV1], max_height=1080) == ["v_av1_1080", "a_aac"]


class TestAudioProfilesIgnoreMaxHeight:
    @pytest.mark.parametrize("api_value", ["mp3", "best_audio"])
    def test_opts_unchanged_by_limit(self, api_value):
        profile = get_profile(api_value)
        assert profile.yt_dlp_opts(max_height=720) == profile.yt_dlp_opts()


class TestDownloadVideoMaxHeight:
    """``download_video`` reads the add-on option from MAX_VIDEO_HEIGHT (exported by run.sh)."""

    @staticmethod
    def _format_for(profile, monkeypatch, env_value):
        from unittest.mock import MagicMock, patch

        from app.yt_dlp_manager import download_video

        if env_value is None:
            monkeypatch.delenv("MAX_VIDEO_HEIGHT", raising=False)
        else:
            monkeypatch.setenv("MAX_VIDEO_HEIGHT", env_value)
        with patch("app.yt_dlp_manager.yt_dlp.YoutubeDL") as ydl:
            ydl.return_value.__enter__.return_value = MagicMock(extract_info=MagicMock(return_value={}))
            download_video("https://x", output_dir="/d", profile=profile)
        return ydl.call_args[0][0]["format"]

    @pytest.mark.parametrize("api_value", ["mp4", "best_video"])
    def test_video_profiles_capped_when_set(self, api_value, monkeypatch):
        fmt = self._format_for(get_profile(api_value), monkeypatch, "2160")
        assert fmt == get_profile(api_value).yt_dlp_opts(max_height=2160)["format"]
        assert fmt != get_profile(api_value).yt_dlp_opts()["format"]

    @pytest.mark.parametrize("api_value", ["mp4", "best_video", "mp3", "best_audio"])
    def test_unchanged_when_unset(self, api_value, monkeypatch):
        assert self._format_for(get_profile(api_value), monkeypatch, None) == get_profile(api_value).yt_dlp_opts()["format"]

    @pytest.mark.parametrize("env_value", ["", "  ", "abc", "0", "-1", "1080.5"])
    def test_invalid_value_is_ignored(self, env_value, monkeypatch):
        assert self._format_for(BEST_VIDEO, monkeypatch, env_value) == BEST_VIDEO.yt_dlp_opts()["format"]
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


class TestBestAudio:
    def test_registered_and_allowed(self):
        from app.profiles import ALLOWED_VALUES, BEST_AUDIO, get_profile

        assert get_profile("best_audio") is BEST_AUDIO
        assert "best_audio" in ALLOWED_VALUES

    def test_selector_prefers_opus_then_any_best_audio(self):
        from app.profiles import BEST_AUDIO

        branches = BEST_AUDIO.yt_dlp_opts()["format"].split("/")
        assert branches[0] == "bestaudio[acodec=opus]"
        assert len(branches) > 1

    def test_never_re_encodes(self):
        """Stream copy only: 'best' keeps the source codec and sets no bitrate."""
        from app.profiles import BEST_AUDIO

        pps = BEST_AUDIO.yt_dlp_opts()["postprocessors"]
        assert len(pps) == 1
        assert pps[0]["key"] == "FFmpegExtractAudio"
        assert pps[0]["preferredcodec"] == "best"
        assert "preferredquality" not in pps[0]
        assert BEST_AUDIO.faststart is False

    def test_filename_suffix(self):
        from app.profiles import BEST_AUDIO

        assert BEST_AUDIO.filename_suffix == " [best]"

    def test_outtmpl_includes_suffix(self):
        from unittest.mock import MagicMock, patch

        from app.profiles import BEST_AUDIO
        from app.yt_dlp_manager import download_video

        with patch("app.yt_dlp_manager.yt_dlp.YoutubeDL") as ydl:
            ydl.return_value.__enter__.return_value = MagicMock(extract_info=MagicMock(return_value={}))
            download_video("https://x", output_dir="/d", profile=BEST_AUDIO)
        assert ydl.call_args[0][0]["outtmpl"] == "/d/%(title)s [best].%(ext)s"

    def test_selector_picks_opus_over_higher_bitrate_aac(self):
        formats = [
            _fmt("aac", "m4a", "none", "mp4a.40.2"),
            _fmt("opus", "webm", "none", "opus"),
        ]
        formats[0]["abr"] = 256
        formats[1]["abr"] = 128
        assert _pick_best_audio(formats) == ["opus"]

    def test_selector_falls_back_to_aac_only_source(self):
        assert _pick_best_audio([_fmt("aac", "m4a", "none", "mp4a.40.2")]) == ["aac"]

    def test_selector_falls_back_to_progressive_when_no_audio_only_stream(self):
        """E.g. a YouTube SABR session that offers only format 18 (H.264 + AAC in MP4)."""
        formats = [_fmt("18", "mp4", "avc1.42001E", "mp4a.40.2", height=240)]
        assert _pick_best_audio(formats) == ["18"]

    def test_selector_prefers_copyable_audio_only_over_uncopyable(self):
        formats = [
            _fmt("vorbis", "webm", "none", "vorbis"),
            _fmt("eac3", "mp4", "none", "ec-3"),
        ]
        assert _pick_best_audio(formats) == ["vorbis"]

    def test_selector_rejects_source_with_only_uncopyable_audio(self):
        """yt-dlp would re-encode such audio to MP3; failing the download keeps the no-re-encode promise."""
        formats = [
            _fmt("eac3", "mp4", "none", "ec-3"),
            _fmt("prog", "mp4", "avc1.640028", "ec-3", height=1080),
        ]
        assert _pick_best_audio(formats) == []


def _pick_best_audio(formats):
    """Format ids yt-dlp would download for the Best Audio profile (formats ordered worst → best)."""
    import yt_dlp
    from app.profiles import BEST_AUDIO

    ydl = yt_dlp.YoutubeDL({"quiet": True})
    selector = ydl.build_format_selector(BEST_AUDIO.yt_dlp_opts()["format"])
    return [f["format_id"] for f in selector({"formats": formats, "incomplete_formats": False})]


class TestBestAudioPostProcessing:
    """Runs the configured FFmpegExtractAudio with a mocked codec probe and ffmpeg call."""

    @staticmethod
    def _run(tmp_path, ext, codec):
        from unittest.mock import patch

        import yt_dlp
        from app.profiles import BEST_AUDIO
        from yt_dlp.postprocessor import FFmpegExtractAudioPP

        (pp_opts,) = BEST_AUDIO.yt_dlp_opts()["postprocessors"]
        pp = FFmpegExtractAudioPP(
            yt_dlp.YoutubeDL({"quiet": True}), **{k: v for k, v in pp_opts.items() if k != "key"},
        )
        src = tmp_path / f"Song [best].{ext}"
        src.write_bytes(b"audio")

        def fake_ffmpeg(_path, out_path, _codec, _opts):
            with open(out_path, "wb") as f:
                f.write(b"converted")

        with patch.object(pp, "get_audio_codec", return_value=codec), \
                patch.object(pp, "run_ffmpeg", side_effect=fake_ffmpeg) as run_ffmpeg:
            _, info = pp.run({"filepath": str(src), "ext": ext})
        return info["filepath"], run_ffmpeg

    def test_opus_in_webm_is_copied_to_opus(self, tmp_path):
        path, run_ffmpeg = self._run(tmp_path, "webm", "opus")

        assert path.endswith("Song [best].opus")
        assert run_ffmpeg.call_args.args[2] == "copy"

    def test_aac_in_m4a_is_left_untouched(self, tmp_path):
        path, run_ffmpeg = self._run(tmp_path, "m4a", "aac")

        assert path.endswith("Song [best].m4a")
        run_ffmpeg.assert_not_called()

    def test_vorbis_in_webm_is_copied_to_ogg(self, tmp_path):
        path, run_ffmpeg = self._run(tmp_path, "webm", "vorbis")

        assert path.endswith("Song [best].ogg")
        assert run_ffmpeg.call_args.args[2] == "copy"

    def test_aac_in_progressive_mp4_is_copied_to_m4a(self, tmp_path):
        path, run_ffmpeg = self._run(tmp_path, "mp4", "aac")

        assert path.endswith("Song [best].m4a")
        assert run_ffmpeg.call_args.args[2] == "copy"
