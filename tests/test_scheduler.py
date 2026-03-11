"""
Tests for APScheduler integration — Story 2.3.

Covers:
  - update_yt_dlp_scheduled() deferral logic (AC3, AC4, AC5)
  - create_app() scheduler initialization (AC2, AC6)

Run with:
    cd /repo && PYTHONPATH=yt-dlp-api pytest tests/test_scheduler.py -v
"""
import atexit
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

import app as app_module
from app import update_yt_dlp_scheduled


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_scheduler():
    """Return a MagicMock that stands in for BackgroundScheduler."""
    mock = MagicMock()
    return mock


def _make_mock_updater(is_updating=False):
    """Return a MagicMock Updater with configurable is_updating() return value."""
    mock = MagicMock()
    mock.is_updating.return_value = is_updating
    return mock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_deferral_count():
    """Reset the module-level deferral counter before each test."""
    app_module._deferral_count[0] = 0
    yield
    app_module._deferral_count[0] = 0


@pytest.fixture()
def mock_scheduler():
    """Patch module-level _scheduler with a MagicMock."""
    mock = _make_mock_scheduler()
    original = app_module._scheduler
    app_module._scheduler = mock
    yield mock
    app_module._scheduler = original


# ---------------------------------------------------------------------------
# AC3 — no active tasks → update_if_needed("scheduled") called, counter reset
# ---------------------------------------------------------------------------

class TestScheduledJobNoActiveTasks:
    def test_calls_update_if_needed_scheduled(self, mock_scheduler):
        """No active tasks → updater.update_if_needed('scheduled') is called."""
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        mock_updater.update_if_needed.assert_called_once_with("scheduled")

    def test_deferral_count_reset_to_zero(self, mock_scheduler):
        """Counter is reset to 0 on successful (non-deferred) execution."""
        app_module._deferral_count[0] = 2  # simulate previous deferrals
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 0

    def test_restores_cron_trigger_after_success(self, mock_scheduler):
        """CronTrigger(hour=3) is restored after successful execution."""
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        # reschedule_job should be called with a CronTrigger
        mock_scheduler.reschedule_job.assert_called_once()
        call_args = mock_scheduler.reschedule_job.call_args
        assert call_args[0][0] == "yt_dlp_update"
        from apscheduler.triggers.cron import CronTrigger
        assert isinstance(call_args[1]["trigger"], CronTrigger)

    def test_no_update_if_updater_is_none(self, mock_scheduler):
        """Handles gracefully when _updater is None (edge case: called before init)."""
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", None):
            update_yt_dlp_scheduled()
        # reschedule_job is still called
        mock_scheduler.reschedule_job.assert_called_once()


# ---------------------------------------------------------------------------
# AC4 — active tasks → reschedule +5 min, log attempt N/3
# ---------------------------------------------------------------------------

class TestScheduledJobDeferral:
    def test_attempt_1_reschedules_with_date_trigger(self, mock_scheduler):
        """First deferral: job rescheduled with DateTrigger +5 min."""
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 1
        mock_scheduler.reschedule_job.assert_called_once()
        call_args = mock_scheduler.reschedule_job.call_args
        assert call_args[0][0] == "yt_dlp_update"
        from apscheduler.triggers.date import DateTrigger
        assert isinstance(call_args[1]["trigger"], DateTrigger)

    def test_attempt_1_does_not_call_update_if_needed(self, mock_scheduler):
        """On deferral, update_if_needed is NOT called."""
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        mock_updater.update_if_needed.assert_not_called()

    def test_attempt_2_increments_counter(self, mock_scheduler):
        """Second consecutive deferral: counter increments to 2."""
        app_module._deferral_count[0] = 1
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 2

    def test_attempt_3_increments_counter(self, mock_scheduler):
        """Third consecutive deferral: counter increments to 3."""
        app_module._deferral_count[0] = 2
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 3

    def test_is_updating_also_triggers_deferral(self, mock_scheduler):
        """Deferral triggers when updater.is_updating() is True (even if no active tasks)."""
        mock_updater = _make_mock_updater(is_updating=True)
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 1
        mock_updater.update_if_needed.assert_not_called()

    def test_deferral_log_message_contains_attempt_info(self, mock_scheduler, caplog):
        """Log message includes '(attempt N/3)' for deferral."""
        import logging
        mock_updater = _make_mock_updater(is_updating=False)
        with caplog.at_level(logging.WARNING, logger="app"), \
             patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert "attempt 1/3" in caplog.text
        assert "[SCHEDULER]" in caplog.text


# ---------------------------------------------------------------------------
# AC5 — 3 consecutive deferrals → max reached, CronTrigger restored, counter reset
# ---------------------------------------------------------------------------

class TestScheduledJobMaxDeferrals:
    def test_4th_deferral_hits_max(self, mock_scheduler):
        """After 3 deferrals, 4th call with active tasks logs max and resets counter."""
        app_module._deferral_count[0] = 3  # simulate 3 previous deferrals
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 0
        mock_updater.update_if_needed.assert_not_called()

    def test_max_deferral_restores_cron_trigger(self, mock_scheduler):
        """After max deferrals, CronTrigger(hour=3) is restored."""
        app_module._deferral_count[0] = 3
        mock_updater = _make_mock_updater(is_updating=False)
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        mock_scheduler.reschedule_job.assert_called_once()
        call_args = mock_scheduler.reschedule_job.call_args
        assert call_args[0][0] == "yt_dlp_update"
        from apscheduler.triggers.cron import CronTrigger
        assert isinstance(call_args[1]["trigger"], CronTrigger)

    def test_max_deferral_log_message(self, mock_scheduler, caplog):
        """Log message 'Max deferrals reached, skipping update' emitted at max."""
        import logging
        app_module._deferral_count[0] = 3
        mock_updater = _make_mock_updater(is_updating=False)
        with caplog.at_level(logging.WARNING, logger="app"), \
             patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert "Max deferrals reached, skipping update" in caplog.text

    def test_counter_resets_allow_next_cycle(self, mock_scheduler):
        """After max deferral reset, the next call with no active tasks runs normally."""
        app_module._deferral_count[0] = 3
        mock_updater = _make_mock_updater(is_updating=False)
        # First call: max deferral
        with patch("app.api.has_active_tasks", return_value=True), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        assert app_module._deferral_count[0] == 0
        mock_scheduler.reset_mock()

        # Second call: no active tasks → normal execution
        with patch("app.api.has_active_tasks", return_value=False), \
             patch("app.api._updater", mock_updater):
            update_yt_dlp_scheduled()

        mock_updater.update_if_needed.assert_called_once_with("scheduled")


# ---------------------------------------------------------------------------
# AC2 / AC6 — create_app() scheduler initialization
# ---------------------------------------------------------------------------

class TestCreateAppSchedulerInit:
    def test_scheduler_job_registered_with_cron_trigger(self, tmp_path):
        """create_app() registers 'yt_dlp_update' job with CronTrigger(hour=3)."""
        from apscheduler.triggers.cron import CronTrigger
        state_file = tmp_path / "state.json"
        application = app_module.create_app(state_path=str(state_file))
        application.config["TESTING"] = True

        scheduler = app_module._scheduler
        assert scheduler is not None
        job = scheduler.get_job("yt_dlp_update")
        assert job is not None
        assert isinstance(job.trigger, CronTrigger)
        scheduler.shutdown(wait=False)

    def test_scheduler_is_running_after_create_app(self, tmp_path):
        """Scheduler is started (running state) after create_app()."""
        state_file = tmp_path / "state.json"
        app_module.create_app(state_path=str(state_file))

        assert app_module._scheduler is not None
        assert app_module._scheduler.running
        app_module._scheduler.shutdown(wait=False)

    def test_atexit_registered_for_shutdown(self, tmp_path):
        """atexit.register is called with scheduler.shutdown during create_app()."""
        state_file = tmp_path / "state.json"
        with patch("atexit.register") as mock_atexit:
            app_module.create_app(state_path=str(state_file))

        # atexit.register should have been called at least once during create_app()
        assert mock_atexit.called
        # Verify a callable (the shutdown lambda) was registered
        assert any(callable(c[0][0]) for c in mock_atexit.call_args_list)
        app_module._scheduler.shutdown(wait=False)
