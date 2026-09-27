import os
import re
import uuid
from pathlib import Path
from fastapi import UploadFile


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    name = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return f"{name}{ext.lower()}"


def generate_unique_filename(filename: str) -> str:
    safe_name = sanitize_filename(filename)
    name, ext = os.path.splitext(safe_name)
    unique_id = uuid.uuid4().hex[:8]
    return f"{name}_{unique_id}{ext}"


async def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    with destination.open("wb") as buffer:
        while True:
            chunk = await upload_file.read(1024 * 1024)
            if not chunk:
                break
            buffer.write(chunk)
    await upload_file.close()