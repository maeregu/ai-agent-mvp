from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.config import OUTPUT_DIR, SHORT_CLIP_SECONDS, VIDEO_EXTENSIONS


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def generate_short_clip(
    source_path: Path,
    job_id: str,
    start_seconds: float = 0,
    end_seconds: float | None = None,
    clip_index: int = 1,
    duration_seconds: int | None = None,
) -> Path | None:
    if not is_video_file(source_path):
        return None
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("FFmpeg is required to generate short video clips.")

    duration = duration_seconds or int(os.getenv("SHORT_CLIP_SECONDS", str(SHORT_CLIP_SECONDS)))
    if end_seconds is not None:
        duration = max(3, min(duration, int(round(end_seconds - start_seconds))))
    output_path = OUTPUT_DIR / f"{job_id}_short_{clip_index}.mp4"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.BELOW_NORMAL_PRIORITY_CLASS

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(max(0, round(start_seconds, 2))),
            "-i",
            str(source_path),
            "-t",
            str(duration),
            "-vf",
            "scale=720:-2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=duration + 180,
        creationflags=creationflags,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Short video generation failed: {message}")
    return output_path
