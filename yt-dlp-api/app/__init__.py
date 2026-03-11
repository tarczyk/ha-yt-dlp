import atexit
import logging
import threading
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from flask import Flask, request

logger = logging.getLogger(__name__)

# Module-level scheduler instance — set in create_app(), used by update_yt_dlp_scheduled()
_scheduler: BackgroundScheduler | None = None

# Mutable list so update_yt_dlp_scheduled() can modify without nonlocal keyword.
# Tracks consecutive deferrals; resets on successful execution or max deferral.
_deferral_count: list[int] = [0]


def update_yt_dlp_scheduled() -> None:
    """Scheduled job: run yt-dlp update at 03:00 with active-task deferral logic.

    Defers up to 3 times (+5 min each) if active downloads exist.
    After 3 consecutive deferrals with active tasks, skips the update and
    restores CronTrigger(hour=3) so the next attempt is the following day.
    """
    if _scheduler is None:
        logger.error("[SCHEDULER] Scheduler not initialized — cannot execute scheduled job")
        return

    # Lazy import avoids circular imports at module load time and ensures
    # _updater is accessed at call time (not captured as None during init).
    from . import api as _api_module

    _updater = _api_module._updater

    if _api_module.has_active_tasks() or (_updater and _updater.is_updating()):
        _deferral_count[0] += 1
        attempt = _deferral_count[0]
        logger.warning("[SCHEDULER] Active tasks found, deferring update (attempt %d/3)", attempt)
        if attempt <= 3:
            next_run = datetime.now(timezone.utc) + timedelta(minutes=5)
            _scheduler.reschedule_job("yt_dlp_update", trigger=DateTrigger(run_date=next_run))
        else:
            logger.warning("[SCHEDULER] Max deferrals reached, skipping update")
            _deferral_count[0] = 0
            _scheduler.reschedule_job("yt_dlp_update", trigger=CronTrigger(hour=3))
    else:
        _deferral_count[0] = 0
        if _updater:
            _updater.update_if_needed("scheduled")
        # Restore CronTrigger in case job was running with a DateTrigger (deferred execution)
        _scheduler.reschedule_job("yt_dlp_update", trigger=CronTrigger(hour=3))


def create_app(state_path: str = "/data/update-state.json") -> Flask:
    global _scheduler

    app = Flask(__name__)
    from .api import api
    app.register_blueprint(api)

    # Initialize Updater (loads state_path; gracefully handles missing file)
    from .updater import Updater
    from .api import init_updater
    init_updater(Updater(state_path=state_path))

    # Kick off a background version check at startup so the cache is warm
    # and a WARNING is emitted early if yt-dlp is outdated.
    from .yt_dlp_manager import check_ytdlp_version
    threading.Thread(target=check_ytdlp_version, daemon=True, name="yt-dlp-version-check").start()

    # APScheduler: daily yt-dlp auto-update at 03:00.
    # CronTrigger(hour=3) fires at next 03:00 — NOT immediately on startup (NFR6, NFR12).
    # atexit ensures graceful shutdown when the Flask process exits.
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(update_yt_dlp_scheduled, trigger=CronTrigger(hour=3), id="yt_dlp_update")
    atexit.register(lambda: _scheduler.shutdown() if _scheduler and _scheduler.running else None)
    _scheduler.start()

    # CORS: card runs in browser (HA origin), API on different port → browser blocks without this
    @app.after_request
    def _cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    @app.before_request
    def _cors_preflight():
        if request.method == "OPTIONS":
            return "", 204

    return app
