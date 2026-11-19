import pytest
from unittest.mock import patch, MagicMock


def test_ytdlp_remote_components():
    """Verify that yt-dlp YoutubeDL can be instantiated and extract_info is callable."""
    import yt_dlp

    ydl_opts = {"quiet": True, "skip_download": True}
    mock_info = {"id": "dQw4w9WgXcQ", "title": "Test Video", "url": "https://example.com/video.mp4"}

    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = mock_info
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)

    assert info["id"] == "dQw4w9WgXcQ"
    assert info["title"] == "Test Video"
    mock_ydl_instance.extract_info.assert_called_once_with(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False
    )


def test_download_video_mp3_uses_audio_format():
    """Verify that MP3 profile sets bestaudio format and FFmpegExtractAudio postprocessor."""
    from app.profiles import MP3
    from app.yt_dlp_manager import download_video

    captured_opts = {}

    def fake_ydl_class(opts):
        captured_opts.update(opts)
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        instance.extract_info.return_value = {"title": "Test"}
        return instance

    with patch("yt_dlp.YoutubeDL", side_effect=fake_ydl_class):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", profile=MP3)

    assert captured_opts["format"] == "bestaudio/best"
    assert any(p["key"] == "FFmpegExtractAudio" for p in captured_opts.get("postprocessors", []))


def test_download_video_mp4_uses_video_format():
    """Verify that MP4 profile sets the bestvideo+bestaudio format string."""
    from app.profiles import MP4
    from app.yt_dlp_manager import download_video

    captured_opts = {}

    def fake_ydl_class(opts):
        captured_opts.update(opts)
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        instance.extract_info.return_value = {"title": "Test"}
        return instance

    with patch("yt_dlp.YoutubeDL", side_effect=fake_ydl_class):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", profile=MP4)

    assert "mp4" in captured_opts["format"]
    assert captured_opts.get("merge_output_format") == "mp4"


def test_download_video_unknown_profile_raises_value_error():
    """Verify that an unknown profile or format_type raises ValueError instead of silent fallback."""
    from app.yt_dlp_manager import download_video

    with pytest.raises(ValueError, match="Unknown download profile: invalid"):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", profile="invalid")

    with pytest.raises(ValueError, match="Unknown download profile: unknown"):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", format_type="unknown")


def test_download_video_uses_cookies_file_when_present(tmp_path, monkeypatch):
    """Verify COOKIES_FILE env is passed to yt-dlp when the file exists."""
    from app.yt_dlp_manager import download_video

    cookies = tmp_path / "youtube_cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    monkeypatch.setenv("COOKIES_FILE", str(cookies))

    captured_opts = {}

    def fake_ydl_class(opts):
        captured_opts.update(opts)
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        instance.extract_info.return_value = {"title": "Test"}
        return instance

    with patch("yt_dlp.YoutubeDL", side_effect=fake_ydl_class):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert captured_opts.get("cookiefile") == str(cookies)


def test_download_video_skips_missing_cookies_file(tmp_path, monkeypatch):
    """Verify missing COOKIES_FILE does not break downloads."""
    from app.yt_dlp_manager import download_video

    monkeypatch.setenv("COOKIES_FILE", str(tmp_path / "missing.txt"))

    captured_opts = {}

    def fake_ydl_class(opts):
        captured_opts.update(opts)
        instance = MagicMock()
        instance.__enter__ = MagicMock(return_value=instance)
        instance.__exit__ = MagicMock(return_value=False)
        instance.extract_info.return_value = {"title": "Test"}
        return instance

    with patch("yt_dlp.YoutubeDL", side_effect=fake_ydl_class):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert "cookiefile" not in captured_opts


def test_download_timeout():
    """Verify that a socket timeout triggers an exception during download."""
    from app.yt_dlp_manager import download_video

    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.side_effect = Exception("socket timeout")
        mock_ydl_class.return_value.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_class.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(Exception, match="socket timeout"):
            download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", timeout=1)


def _download_with_fake_ydl(profile):
    from app.yt_dlp_manager import download_video

    instance = MagicMock()
    instance.__enter__ = MagicMock(return_value=instance)
    instance.__exit__ = MagicMock(return_value=False)
    instance.extract_info.return_value = {"title": "Test"}

    with patch("yt_dlp.YoutubeDL", return_value=instance):
        download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", profile=profile)
    return instance


def test_download_video_mp4_adds_faststart_postprocessor():
    from app.postprocessors import FastStartPP
    from app.profiles import MP4

    ydl = _download_with_fake_ydl(MP4)

    (pp,), kwargs = ydl.add_post_processor.call_args
    assert isinstance(pp, FastStartPP)
    assert kwargs == {"when": "after_move"}


def test_download_video_mp3_has_no_faststart_postprocessor():
    from app.profiles import MP3

    assert not _download_with_fake_ydl(MP3).add_post_processor.called
