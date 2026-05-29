from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.config import SHORT_CLIP_COUNT, SHORT_CLIP_SECONDS
from app.database import job_store
from app.models import TranscriptionJob
from app.routes.jobs import to_response
from app.schemas import JobResponse
from app.services.file_storage import save_upload
from app.workers.tasks import enqueue_transcription_job

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=JobResponse)
def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_language: str = Form("en"),
    clip_duration_seconds: int = Form(SHORT_CLIP_SECONDS),
    clip_count: int = Form(SHORT_CLIP_COUNT),
) -> JobResponse:
    if target_language not in {"am", "en", "none"}:
        raise HTTPException(status_code=400, detail="target_language must be am, en, or none")
    if clip_duration_seconds not in {45, 120, 300, 1200}:
        raise HTTPException(status_code=400, detail="clip_duration_seconds must be 45, 120, 300, or 1200")
    if clip_count < 1 or clip_count > 5:
        raise HTTPException(status_code=400, detail="clip_count must be between 1 and 5")

    try:
        original_filename, source_path = save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = TranscriptionJob(
        id=uuid4().hex,
        filename=original_filename,
        source_path=source_path,
        target_language=target_language,
        clip_duration_seconds=clip_duration_seconds,
        clip_count=clip_count,
    )
    job_store.add(job)
    enqueue_transcription_job(job.id, background_tasks)
    return to_response(job)

