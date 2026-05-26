from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_MB, UPLOAD_DIR


def validate_upload(file: UploadFile) -> str:
    filename = file.filename or "upload"
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Allowed: {allowed}")
    return extension


def save_upload(file: UploadFile) -> tuple[str, Path]:
    extension = validate_upload(file)
    safe_name = f"{uuid4().hex}{extension}"
    destination = UPLOAD_DIR / safe_name

    size = 0
    with destination.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_MB * 1024 * 1024:
                destination.unlink(missing_ok=True)
                raise ValueError(f"File too large. Limit is {MAX_UPLOAD_MB} MB.")
            buffer.write(chunk)

    return file.filename or safe_name, destination


def copy_demo_file(source: Path, destination: Path) -> None:
    shutil.copyfile(source, destination)

