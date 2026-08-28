"""POST /api/jobs — upload one or more audio files and create a job.

When multiple files are provided they are merged into a single audio
stream before transcription, so the result is one combined transcript
and summary rather than separate outputs per file.
"""
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
from app.utils.audio import merge_audio_files, split_audio

router = APIRouter()


@router.post("", response_model=JobCreateResponse)
async def upload_audio(
    files: list[UploadFile],
    beam_size: int = Form(default=2),
    language: str = Form(default=AUTO_DETECT),
    store: JobStore = Depends(get_job_store),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}' in '{f.filename}'. "
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

    async def _save(upload: UploadFile) -> str:
        ext = os.path.splitext(upload.filename or "")[1].lower()
        path = os.path.join(settings.downloads_dir, f"{uuid.uuid4()}{ext}")
        data = await upload.read()
        await asyncio.to_thread(_write, path, data)
        return path

    def _write(path: str, data: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(data)

    saved_paths = await asyncio.gather(*(_save(f) for f in files))
    saved_paths = list(saved_paths)

    if len(saved_paths) > 1:
        merged_path = await asyncio.to_thread(merge_audio_files, saved_paths)
        for p in saved_paths:
            try:
                os.unlink(p)
            except OSError:
                pass
        primary_path = merged_path
        display_name = f"{len(files)} files merged"
    else:
        primary_path = saved_paths[0]
        display_name = files[0].filename or "audio"

    chunk_paths = await asyncio.to_thread(split_audio, primary_path)
    is_chunked = len(chunk_paths) > 1

    job = store.create(
        filename=display_name,
        audio_path=primary_path,
        beam_size=max(1, min(beam_size, 5)),
        language=transcription_language,
        chunk_paths=chunk_paths if is_chunked else [],
    )
    return JobCreateResponse(job_id=job.id, status=job.status)
