"""Runtime registry for task scheduler state."""
from typing import Optional


_scheduler = None


def set_scheduler(scheduler) -> None:
    global _scheduler
    _scheduler = scheduler


def get_scheduler():
    return _scheduler


def get_scheduler_status() -> dict:
    if _scheduler is None:
        return {
            "running": False,
            "next_run_time": None,
            "enqueue_interval": None,
            "workers_total": 0,
            "workers_active": 0,
        }
    return _scheduler.get_status()
