from __future__ import annotations

import os
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    HIGHLIGHT_PROVIDER,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CHUNK_DIR,
    JOB_DIR,
    OPENAI_HIGHLIGHT_MODEL,
    OPENAI_TRANSLATION_MODEL,
    OUTPUT_DIR,
    SHORT_CLIP_SECONDS,
    SHORT_CLIP_COUNT,
    TRANSCRIPTION_CHUNK_SECONDS,
    TRANSLATION_PROVIDER,
    UPLOAD_DIR,
    WHISPER_MODEL,
    WHISPER_THREADS,
    WHISPER_TIMEOUT_SECONDS,
    USE_CELERY,
)
from app.routes import jobs, uploads

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOB_DIR.mkdir(parents=True, exist_ok=True)
CHUNK_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Amharic-English Transcription Agent MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(uploads.router)
app.include_router(jobs.router)


def key_fingerprint(value: str | None) -> dict[str, str | int | bool]:
    if not value:
        return {"available": False}
    return {
        "available": True,
        "length": len(value),
        "prefix": value[:7],
        "suffix": value[-4:],
    }


@app.get("/")
def health_check() -> dict[str, str | int | bool | dict[str, str | int | bool]]:
    return {
        "status": "ok",
        "service": "transcription-agent",
        "transcription_provider": os.getenv("TRANSCRIPTION_PROVIDER", "local_whisper"),
        "whisper_model": os.getenv("WHISPER_MODEL", WHISPER_MODEL),
        "whisper_threads": os.getenv("WHISPER_THREADS", str(WHISPER_THREADS)),
        "whisper_timeout_seconds": os.getenv("WHISPER_TIMEOUT_SECONDS", str(WHISPER_TIMEOUT_SECONDS)),
        "whisper_available": shutil.which("whisper") is not None,
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
        "translation_provider": os.getenv("TRANSLATION_PROVIDER", TRANSLATION_PROVIDER),
        "openai_translation_model": os.getenv("OPENAI_TRANSLATION_MODEL", OPENAI_TRANSLATION_MODEL),
        "openai_api_key_available": bool(os.getenv("OPENAI_API_KEY")),
        "openai_api_key_fingerprint": key_fingerprint(os.getenv("OPENAI_API_KEY")),
        "short_clip_seconds": os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)),
        "short_clip_count": os.getenv("SHORT_CLIP_COUNT", str(SHORT_CLIP_COUNT)),
        "transcription_chunk_seconds": os.getenv("TRANSCRIPTION_CHUNK_SECONDS", str(TRANSCRIPTION_CHUNK_SECONDS)),
        "use_celery": os.getenv("USE_CELERY", USE_CELERY),
        "celery_broker_url": os.getenv("CELERY_BROKER_URL", CELERY_BROKER_URL),
        "celery_result_backend": os.getenv("CELERY_RESULT_BACKEND", CELERY_RESULT_BACKEND),
        "highlight_provider": os.getenv("HIGHLIGHT_PROVIDER", HIGHLIGHT_PROVIDER),
        "openai_highlight_model": os.getenv("OPENAI_HIGHLIGHT_MODEL", OPENAI_HIGHLIGHT_MODEL),
    }
