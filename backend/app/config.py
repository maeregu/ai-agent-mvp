from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            import os

            os.environ[key] = value


load_local_env()

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
JOB_DIR = BASE_DIR / "jobs"
CHUNK_DIR = BASE_DIR / "chunks"
MAX_UPLOAD_MB = 500
WHISPER_MODEL = "tiny"
WHISPER_THREADS = 2
WHISPER_TIMEOUT_SECONDS = 10 * 60
TRANSCRIPTION_CHUNK_SECONDS = 20 * 60
TRANSLATION_PROVIDER = "openai"
OPENAI_TRANSLATION_MODEL = "gpt-5-mini"
SHORT_CLIP_SECONDS = 45
SHORT_CLIP_COUNT = 3
USE_CELERY = "false"
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
HIGHLIGHT_PROVIDER = "openai"
OPENAI_HIGHLIGHT_MODEL = "gpt-5-mini"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".mov",
    ".webm",
    ".ogg",
}

