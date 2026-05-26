from __future__ import annotations

from threading import Lock

from app.config import OUTPUT_DIR
from app.database import job_store
from app.services.highlight_selector import select_highlight
from app.services.transcription import transcribe_media_with_segments
from app.services.translation import translate_text
from app.services.video_shortener import generate_short_clip

transcription_lock = Lock()


def process_transcription_job(job_id: str) -> None:
    job = job_store.get(job_id)
    if job is None:
        return

    try:
        job_store.update(job_id, status="processing")
        with transcription_lock:
            transcription = transcribe_media_with_segments(job.source_path)
        transcript = transcription.text
        segments = transcription.segments

        translation = ""
        translation_error = None
        try:
            translation = translate_text(transcript, job.target_language)
        except Exception as exc:
            translation_error = str(exc)

        highlight = select_highlight(segments, transcript)

        output_path = OUTPUT_DIR / f"{job.id}.txt"
        sections = [f"Transcript\n==========\n{transcript}"]
        if translation:
            sections.append(f"Translation\n===========\n{translation}")
        if highlight:
            sections.append(
                "Selected Highlight\n==================\n"
                f"Start: {highlight.start:.2f}s\n"
                f"End: {highlight.end:.2f}s\n"
                f"Reason: {highlight.reason}"
            )
        if translation_error:
            sections.append(f"Translation Error\n=================\n{translation_error}")
        output_path.write_text("\n\n".join(sections), encoding="utf-8")

        short_video_path = None
        short_video_error = None
        try:
            if highlight:
                short_video_path = generate_short_clip(
                    job.source_path,
                    job.id,
                    start_seconds=highlight.start,
                    end_seconds=highlight.end,
                )
            else:
                short_video_path = generate_short_clip(job.source_path, job.id)
        except Exception as exc:
            short_video_error = str(exc)

        error = translation_error
        if short_video_error:
            error = "\n".join(part for part in [error, short_video_error] if part)

        job_store.update(
            job_id,
            status="completed",
            transcript=transcript,
            translation=translation,
            transcript_segments=segments,
            highlight_start=highlight.start if highlight else None,
            highlight_end=highlight.end if highlight else None,
            highlight_reason=highlight.reason if highlight else None,
            error=error,
            output_path=output_path,
            short_video_path=short_video_path,
        )
    except Exception as exc:
        job_store.update(job_id, status="failed", error=str(exc))

