from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


JobStatus = Literal["queued", "processing", "completed", "failed"]


@dataclass
class TranscriptionJob:
    id: str
    filename: str
    source_path: Path
    target_language: str
    clip_duration_seconds: int = 45
    clip_count: int = 3
    status: JobStatus = "queued"
    progress: int = 0
    progress_message: str = "Queued"
    transcript: str | None = None
    translation: str | None = None
    transcript_segments: list[dict[str, Any]] = field(default_factory=list)
    highlights: list[dict[str, Any]] = field(default_factory=list)
    highlight_start: float | None = None
    highlight_end: float | None = None
    highlight_reason: str | None = None
    error: str | None = None
    output_path: Path | None = None
    short_video_path: Path | None = None
    short_video_paths: list[Path] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

