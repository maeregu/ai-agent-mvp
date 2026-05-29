from __future__ import annotations

import os

from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND


celery_app = Celery(
    "ai_agent_mvp",
    broker=os.getenv("CELERY_BROKER_URL", CELERY_BROKER_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", CELERY_RESULT_BACKEND),
)

celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)

import app.workers.tasks  # noqa: E402,F401
