from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    filename: str
    target_language: str
    clip_duration_seconds: int
    clip_count: int
    status: str
    progress: int
    progress_message: str
    transcript: str | None = None
    translation: str | None = None
    highlights: list[dict] = []
    highlight_start: float | None = None
    highlight_end: float | None = None
    highlight_reason: str | None = None
    error: str | None = None
    download_url: str | None = None
    short_video_url: str | None = None
    short_video_urls: list[str] = []
    created_at: datetime
    updated_at: datetime

