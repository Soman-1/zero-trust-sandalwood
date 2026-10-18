"""Background scheduler that refreshes live area weather for registered trees."""

import threading
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


class TreeEnvironmentScheduler:
    """Periodically stores fresh Open-Meteo readings for active sandalwood trees."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not settings.ENV_REFRESH_ENABLED:
            logger.info("Tree environment refresh scheduler is disabled")
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="tree-env-refresh",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            f"Tree environment refresh scheduler started "
            f"(interval={settings.ENV_REFRESH_INTERVAL_SECONDS}s)"
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("Tree environment refresh scheduler stopped")

    def _run_loop(self) -> None:
        # Initial delay so app startup / seeding finishes first
        initial_wait = min(30, settings.ENV_REFRESH_INTERVAL_SECONDS)
        if self._stop_event.wait(initial_wait):
            return

        while not self._stop_event.is_set():
            try:
                self._refresh_once()
            except Exception as exc:
                logger.warning(f"Scheduled environment refresh failed: {exc}")

            if self._stop_event.wait(settings.ENV_REFRESH_INTERVAL_SECONDS):
                break

    def _refresh_once(self) -> None:
        from app.database.database import SessionLocal
        from app.services.tree_environment_service import TreeEnvironmentService

        with SessionLocal() as db:
            TreeEnvironmentService.refresh_active_trees(db=db)


tree_environment_scheduler = TreeEnvironmentScheduler()
