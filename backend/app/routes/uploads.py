from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from app.database import job_store
from app.models import TranscriptionJob
from app.routes.jobs import to_response
from app.schemas import JobResponse
from app.services.file_storage import save_upload
from app.workers.tasks import process_transcription_job

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=JobResponse)
def upload_media(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target_language: str = Form("en"),
) -> JobResponse:
    if target_language not in {"am", "en", "none"}:
        raise HTTPException(status_code=400, detail="target_language must be am, en, or none")

    try:
        original_filename, source_path = save_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = TranscriptionJob(
        id=uuid4().hex,
        filename=original_filename,
        source_path=source_path,
        target_language=target_language,
    )
    job_store.add(job)
    background_tasks.add_task(process_transcription_job, job.id)
    return to_response(job)

