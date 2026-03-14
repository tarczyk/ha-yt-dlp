"""Integration tests for download UX flow — Story 3.1."""
from unittest.mock import patch

import app.api as api_module
from app.yt_dlp_manager import TASK_STATUS_COMPLETED


class TestDownloadFlow:
    def setup_method(self):
        """Clear shared task state between tests to prevent bleed."""
        with api_module._tasks_lock:
            api_module._tasks.clear()

    # 2.1 — MP4 task creation

    def test_post_download_video_mp4_creates_task(self, client):
        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=test123", "format": "mp4"},
            )
            assert resp.status_code == 202
            data = resp.get_json()
            assert "task_id" in data
            task_id = data["task_id"]
            with api_module._tasks_lock:
                task = api_module._tasks[task_id]
            assert task["format"] == "mp4"
            assert task["status"] == "queued"

    # 2.2 — MP3 task creation

    def test_post_download_video_mp3_task_format_is_mp3(self, client):
        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=test123", "format": "mp3"},
            )
            assert resp.status_code == 202
            data = resp.get_json()
            assert "task_id" in data
            task_id = data["task_id"]
            with api_module._tasks_lock:
                task = api_module._tasks[task_id]
            assert task["format"] == "mp3"
            assert task["status"] == "queued"

    # 2.3 — Invalid URL → 400

    def test_post_download_video_invalid_url_returns_400(self, client):
        resp = client.post(
            "/download_video",
            json={"url": "not-a-url", "format": "mp4"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "invalid url"

    # 2.4 — Playlist URL → 400

    def test_post_download_video_playlist_url_returns_400(self, client):
        resp = client.post(
            "/download_video",
            json={"url": "https://youtube.com/playlist?list=PLtest123", "format": "mp4"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "playlist" in data["error"].lower()

    # 2.5 — GET task with completed status includes title

    def test_get_task_completed_returns_title(self, client):
        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=test123", "format": "mp4"},
            )
        task_id = resp.get_json()["task_id"]
        with api_module._tasks_lock:
            api_module._tasks[task_id]["status"] = TASK_STATUS_COMPLETED
            api_module._tasks[task_id]["title"] = "Test Video Title"
        resp = client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == TASK_STATUS_COMPLETED
        assert "title" in data
        assert data["title"] == "Test Video Title"

    # 2.6 — DELETE queued task → cancelling

    def test_delete_task_cancels_queued_task(self, client):
        with patch("app.api._run_download"):
            resp = client.post(
                "/download_video",
                json={"url": "https://youtube.com/watch?v=test123", "format": "mp4"},
            )
            task_id = resp.get_json()["task_id"]
            resp = client.delete(f"/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "cancelling"
        with api_module._tasks_lock:
            assert api_module._tasks[task_id]["cancelled"] is True

    # 2.7 — GET /config returns media_subdir

    def test_get_config_returns_media_subdir(self, client):
        resp = client.get("/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "media_subdir" in data

    # 2.8 — GET /health includes update_status: "ok"

    def test_get_health_includes_update_status_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "update_status" in data
        assert data["update_status"] == "ok"

    # 2.9 — GET unknown task → 404

    def test_get_unknown_task_returns_404(self, client):
        resp = client.get("/tasks/nonexistent-task-id")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data

    # 2.10 — DELETE unknown task → 404

    def test_delete_unknown_task_returns_404(self, client):
        resp = client.delete("/tasks/nonexistent-task-id")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data
