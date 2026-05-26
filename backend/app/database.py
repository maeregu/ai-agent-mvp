from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from app.models import TranscriptionJob


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, TranscriptionJob] = {}
        self._lock = Lock()

    def add(self, job: TranscriptionJob) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: str) -> TranscriptionJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes: object) -> TranscriptionJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = datetime.now(timezone.utc)
            return job

    def list_recent(self) -> list[TranscriptionJob]:
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda job: job.created_at,
                reverse=True,
            )


job_store = JobStore()

