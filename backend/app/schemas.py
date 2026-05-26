from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    filename: str
    target_language: str
    status: str
    transcript: str | None = None
    translation: str | None = None
    highlight_start: float | None = None
    highlight_end: float | None = None
    highlight_reason: str | None = None
    error: str | None = None
    download_url: str | None = None
    short_video_url: str | None = None
    created_at: datetime
    updated_at: datetime

