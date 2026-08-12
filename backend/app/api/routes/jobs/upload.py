"""POST /api/jobs — upload an audio file and create a job."""
import asyncio
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.api.deps import get_job_store
from app.api.routes.jobs.common import ALLOWED_EXTENSIONS
from app.api.routes.languages import AUTO_DETECT
from app.core.config import settings
from app.models.job import JobStore
from app.schemas.job import JobCreateResponse
from app.services.prompts import LANGUAGE_NAMES
from app.utils.audio import split_audio

router = APIRouter()


@router.post("", response_model=JobCreateResponse)
async def upload_audio(
    file: UploadFile,
    beam_size: int = Form(default=2),
    language: str = Form(default=AUTO_DETECT),
    store: JobStore = Depends(get_job_store),
):
    file_extension = os.path.splitext(file.filename or "")[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    language = language or AUTO_DETECT
    if language != AUTO_DETECT and language not in LANGUAGE_NAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language '{language}'. "
            f"Use '{AUTO_DETECT}' or one of: {', '.join(sorted(LANGUAGE_NAMES))}",
        )
    transcription_language = None if language == AUTO_DETECT else language

    os.makedirs(settings.downloads_dir, exist_ok=True)
    saved_path = os.path.join(settings.downloads_dir, f"{uuid.uuid4()}{file_extension}")
    file_bytes = await file.read()

    def _write_to_disk() -> None:
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

    await asyncio.to_thread(_write_to_disk)

    chunk_paths = await asyncio.to_thread(split_audio, saved_path)
    is_chunked = len(chunk_paths) > 1

    job = store.create(
        filename=file.filename or "audio",
        audio_path=saved_path,
        beam_size=max(1, min(beam_size, 5)),
        language=transcription_language,
        chunk_paths=chunk_paths if is_chunked else [],
    )
    return JobCreateResponse(job_id=job.id, status=job.status)
