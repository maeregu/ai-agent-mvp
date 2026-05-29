from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import CHUNK_DIR, TRANSCRIPTION_CHUNK_SECONDS, WHISPER_MODEL, WHISPER_THREADS, WHISPER_TIMEOUT_SECONDS


@dataclass
class TranscriptionResult:
    text: str
    segments: list[dict[str, Any]] = field(default_factory=list)


def transcribe_media(media_path: Path) -> str:
    return transcribe_media_with_segments(media_path).text


def transcribe_media_with_segments(media_path: Path) -> TranscriptionResult:
    """Transcribe media using the configured MVP provider."""
    provider = os.getenv("TRANSCRIPTION_PROVIDER", "local_whisper").lower()
    if provider == "demo":
        return TranscriptionResult(text=fallback_transcript(media_path), segments=[])
    if provider != "local_whisper":
        raise RuntimeError(f"Unsupported transcription provider: {provider}")
    if shutil.which("whisper") is None:
        raise RuntimeError("Whisper CLI is not installed or not available on PATH.")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg is not installed or not available on PATH. Install FFmpeg, restart the terminal, and start the backend again.")

    chunk_seconds = int(os.getenv("TRANSCRIPTION_CHUNK_SECONDS", str(TRANSCRIPTION_CHUNK_SECONDS)))
    duration = get_media_duration(media_path)
    if duration and duration > chunk_seconds:
        return transcribe_in_chunks(media_path, chunk_seconds)
    return transcribe_single_file(media_path, offset_seconds=0)


def transcribe_single_file(media_path: Path, offset_seconds: float = 0) -> TranscriptionResult:
    model = os.getenv("WHISPER_MODEL", WHISPER_MODEL)
    threads = os.getenv("WHISPER_THREADS", str(WHISPER_THREADS))
    timeout = int(os.getenv("WHISPER_TIMEOUT_SECONDS", str(WHISPER_TIMEOUT_SECONDS)))
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = threads
    env["MKL_NUM_THREADS"] = threads
    env["NUMEXPR_NUM_THREADS"] = threads
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

    try:
        result = subprocess.run(
            [
                "whisper",
                str(media_path),
                "--model",
                model,
                "--language",
                "am",
                "--task",
                "transcribe",
                "--device",
                "cpu",
                "--fp16",
                "False",
                "--threads",
                threads,
                "--output_format",
                "json",
                "--output_dir",
                str(media_path.parent),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            creationflags=creationflags,
        )
    except FileNotFoundError:
        return TranscriptionResult(text=fallback_transcript(media_path), segments=[])
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Transcription timed out after {timeout // 60} minutes. Try a shorter clip, "
            "use WHISPER_MODEL=tiny, or connect a cloud transcription API."
        ) from exc

    output_file = media_path.with_suffix(".json")
    if result.returncode == 0 and output_file.exists():
        payload = json.loads(output_file.read_text(encoding="utf-8"))
        text = str(payload.get("text", "")).strip()
        segments = [
            {
                "start": float(segment.get("start", 0)) + offset_seconds,
                "end": float(segment.get("end", 0)) + offset_seconds,
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in payload.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        return TranscriptionResult(text=text, segments=segments)

    message = result.stderr.strip() or result.stdout.strip()
    if message:
        raise RuntimeError(f"Whisper failed: {message}")
    raise RuntimeError("Whisper failed without an error message.")


def get_media_duration(media_path: Path) -> float | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def transcribe_in_chunks(media_path: Path, chunk_seconds: int) -> TranscriptionResult:
    duration = get_media_duration(media_path) or 0
    job_chunk_dir = CHUNK_DIR / media_path.stem
    job_chunk_dir.mkdir(parents=True, exist_ok=True)

    all_segments: list[dict[str, Any]] = []
    texts: list[str] = []
    start = 0.0
    index = 1
    while start < duration:
        chunk_path = job_chunk_dir / f"chunk_{index:04d}.wav"
        extract_audio_chunk(media_path, chunk_path, start, chunk_seconds)
        result = transcribe_single_file(chunk_path, offset_seconds=start)
        if result.text:
            texts.append(result.text)
        all_segments.extend(result.segments)
        start += chunk_seconds
        index += 1

    return TranscriptionResult(text="\n".join(texts).strip(), segments=all_segments)


def extract_audio_chunk(source_path: Path, chunk_path: Path, start: float, duration: int) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(round(start, 2)),
            "-i",
            str(source_path),
            "-t",
            str(duration),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(chunk_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=duration + 120,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Could not extract audio chunk: {message}")


def fallback_transcript(media_path: Path) -> str:
    return (
        "Demo transcript placeholder.\n\n"
        f"Uploaded file: {media_path.name}\n\n"
        "Set TRANSCRIPTION_PROVIDER=local_whisper after installing Whisper and FFmpeg, "
        "or connect an API provider to replace this with real Amharic-English transcription."
    )

