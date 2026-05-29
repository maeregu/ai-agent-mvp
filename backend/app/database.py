from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import JOB_DIR
from app.models import TranscriptionJob


def serialize_job(job: TranscriptionJob) -> dict[str, Any]:
    data = job.__dict__.copy()
    for key in ["source_path", "output_path", "short_video_path"]:
        value = data.get(key)
        data[key] = str(value) if value else None
    data["short_video_paths"] = [str(path) for path in job.short_video_paths]
    data["created_at"] = job.created_at.isoformat()
    data["updated_at"] = job.updated_at.isoformat()
    return data


def deserialize_job(data: dict[str, Any]) -> TranscriptionJob:
    for key in ["source_path", "output_path", "short_video_path"]:
        if data.get(key):
            data[key] = Path(data[key])
    data["short_video_paths"] = [Path(path) for path in data.get("short_video_paths", [])]
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    data["updated_at"] = datetime.fromisoformat(data["updated_at"])
    return TranscriptionJob(**data)


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, TranscriptionJob] = {}
        self._lock = Lock()
        JOB_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return JOB_DIR / f"{job_id}.json"

    def _persist(self, job: TranscriptionJob) -> None:
        self._path(job.id).write_text(
            json.dumps(serialize_job(job), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self, job_id: str) -> TranscriptionJob | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return deserialize_job(json.loads(path.read_text(encoding="utf-8")))

    def add(self, job: TranscriptionJob) -> None:
        with self._lock:
            self._jobs[job.id] = job
            self._persist(job)

    def get(self, job_id: str) -> TranscriptionJob | None:
        with self._lock:
            job = self._jobs.get(job_id) or self._load(job_id)
            if job:
                self._jobs[job_id] = job
            return job

    def update(self, job_id: str, **changes: object) -> TranscriptionJob | None:
        with self._lock:
            job = self._jobs.get(job_id) or self._load(job_id)
            if job is None:
                return None
            for key, value in changes.items():
                setattr(job, key, value)
            job.updated_at = datetime.now(timezone.utc)
            self._jobs[job_id] = job
            self._persist(job)
            return job

    def list_recent(self) -> list[TranscriptionJob]:
        with self._lock:
            for path in JOB_DIR.glob("*.json"):
                job_id = path.stem
                if job_id not in self._jobs:
                    job = self._load(job_id)
                    if job:
                        self._jobs[job_id] = job
            return sorted(
                self._jobs.values(),
                key=lambda job: job.created_at,
                reverse=True,
            )


job_store = JobStore()

