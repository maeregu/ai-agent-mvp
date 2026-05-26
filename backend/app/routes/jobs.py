from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.database import job_store
from app.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def to_response(job) -> JobResponse:
    return JobResponse(
        id=job.id,
        filename=job.filename,
        target_language=job.target_language,
        status=job.status,
        transcript=job.transcript,
        translation=job.translation,
        highlight_start=job.highlight_start,
        highlight_end=job.highlight_end,
        highlight_reason=job.highlight_reason,
        error=job.error,
        download_url=f"/jobs/{job.id}/download" if job.output_path else None,
        short_video_url=f"/jobs/{job.id}/short-video" if job.short_video_path else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_response(job)


@router.get("/{job_id}/download")
def download_job(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None or job.output_path is None or not job.output_path.exists():
        raise HTTPException(status_code=404, detail="Output not found")
    return FileResponse(job.output_path, filename=f"{job.filename}.txt")


@router.get("/{job_id}/short-video")
def download_short_video(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None or job.short_video_path is None or not job.short_video_path.exists():
        raise HTTPException(status_code=404, detail="Short video not found")
    return FileResponse(job.short_video_path, filename=f"{job.id}_short.mp4", media_type="video/mp4")

