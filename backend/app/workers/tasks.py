from __future__ import annotations

import os
from threading import Lock

from fastapi import BackgroundTasks

from app.config import OUTPUT_DIR, USE_CELERY
from app.database import job_store
from app.services.highlight_selector import Highlight, select_highlights
from app.services.transcription import transcribe_media_with_segments
from app.services.translation import translate_text
from app.services.video_shortener import generate_short_clip

transcription_lock = Lock()


def enqueue_transcription_job(job_id: str, background_tasks: BackgroundTasks) -> None:
    use_celery = os.getenv("USE_CELERY", USE_CELERY).lower() == "true"
    if use_celery:
        try:
            process_transcription_job_task.delay(job_id)
            return
        except Exception as exc:
            job_store.update(
                job_id,
                progress_message=f"Celery enqueue failed; using local background task: {exc}",
            )
    background_tasks.add_task(process_transcription_job, job_id)


def process_transcription_job(job_id: str) -> None:
    job = job_store.get(job_id)
    if job is None:
        return

    try:
        job_store.update(job_id, status="processing", progress=5, progress_message="Starting processing")
        with transcription_lock:
            job_store.update(job_id, progress=15, progress_message="Transcribing media")
            transcription = transcribe_media_with_segments(job.source_path)
        transcript = transcription.text
        segments = transcription.segments

        translation = ""
        translation_error = None
        try:
            job_store.update(job_id, progress=55, progress_message="Translating transcript")
            translation = translate_text(transcript, job.target_language)
        except Exception as exc:
            translation_error = str(exc)

        job_store.update(job_id, progress=65, progress_message="Selecting highlights")
        highlights = select_highlights(
            segments,
            transcript,
            count=job.clip_count,
            duration_seconds=job.clip_duration_seconds,
        )
        primary_highlight = highlights[0] if highlights else None

        output_path = OUTPUT_DIR / f"{job.id}.txt"
        sections = [f"Transcript\n==========\n{transcript}"]
        if translation:
            sections.append(f"Translation\n===========\n{translation}")
        if highlights:
            highlight_lines = []
            for index, highlight in enumerate(highlights, start=1):
                highlight_lines.append(
                    f"Clip {index}: {highlight.start:.2f}s to {highlight.end:.2f}s\n"
                    f"Reason: {highlight.reason}"
                )
            sections.append("Selected Highlights\n===================\n" + "\n\n".join(highlight_lines))
        if translation_error:
            sections.append(f"Translation Error\n=================\n{translation_error}")
        output_path.write_text("\n\n".join(sections), encoding="utf-8")

        job_store.update(job_id, progress=78, progress_message="Generating short video clips")
        short_video_paths = []
        short_video_error = None
        try:
            if highlights:
                for index, highlight in enumerate(highlights, start=1):
                    path = generate_short_clip(
                        job.source_path,
                        job.id,
                        start_seconds=highlight.start,
                        end_seconds=highlight.end,
                        clip_index=index,
                        duration_seconds=job.clip_duration_seconds,
                    )
                    if path:
                        short_video_paths.append(path)
            else:
                path = generate_short_clip(
                    job.source_path,
                    job.id,
                    clip_index=1,
                    duration_seconds=job.clip_duration_seconds,
                )
                if path:
                    short_video_paths.append(path)
        except Exception as exc:
            short_video_error = str(exc)

        error = translation_error
        if short_video_error:
            error = "\n".join(part for part in [error, short_video_error] if part)

        job_store.update(
            job_id,
            status="completed",
            progress=100,
            progress_message="Completed",
            transcript=transcript,
            translation=translation,
            transcript_segments=segments,
            highlights=[highlight.__dict__ for highlight in highlights],
            highlight_start=primary_highlight.start if primary_highlight else None,
            highlight_end=primary_highlight.end if primary_highlight else None,
            highlight_reason=primary_highlight.reason if primary_highlight else None,
            error=error,
            output_path=output_path,
            short_video_path=short_video_paths[0] if short_video_paths else None,
            short_video_paths=short_video_paths,
        )
    except Exception as exc:
        job_store.update(job_id, status="failed", progress_message="Failed", error=str(exc))


try:
    from app.workers.celery_app import celery_app

    process_transcription_job_task = celery_app.task(name="process_transcription_job")(process_transcription_job)
except Exception:
    process_transcription_job_task = None

