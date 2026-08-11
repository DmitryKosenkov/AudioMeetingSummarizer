"""Routes for the audio -> transcript -> summary pipeline:

    1. POST   /api/jobs                     upload audio, creates a Job
    2. GET    /api/jobs/{job_id}/stream     transcribe, streaming text back live
    3. POST   /api/jobs/{job_id}/summarize  summarize the transcript
    4. GET    /api/jobs/{job_id}/download/txt|docx
"""
import asyncio
import contextlib
import logging
import os
import uuid
from typing import cast

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_job_store, get_summarizer, get_transcriber
from app.api.routes.languages import AUTO_DETECT
from app.core.config import settings
from app.exporters.docx_export import render_markdown_summary_to_docx
from app.exporters.txt_export import render_transcript_to_txt
from app.models.job import Job, JobStatus, JobStore
from app.schemas.job import JobCreateResponse, JobStatusResponse, SummaryResponse
from app.services.pipeline import summarize_async
from app.services.prompts import LANGUAGE_NAMES, SummaryType
from app.services.summarizer import SummarizationError, Summarizer
from app.services.transcriber import LanguageDetected, Transcriber
from app.utils.audio import split_audio
from app.utils.sse import sse_event
from app.utils.streaming import StreamEventKind, stream_from_blocking_generator


class SummarizeRequest(BaseModel):
    summary_type: SummaryType = SummaryType.MEETING


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".opus", ".aac"}


def _get_job_or_404(job_id: str, store: JobStore) -> Job:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


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
        with open(saved_path, "wb") as saved_file:
            saved_file.write(file_bytes)

    await asyncio.to_thread(_write_to_disk)

    chunk_paths = await asyncio.to_thread(split_audio, saved_path)
    is_chunked = len(chunk_paths) > 1

    beam_size = max(1, min(beam_size, 5))
    job = store.create(
        filename=file.filename or "audio",
        audio_path=saved_path,
        beam_size=beam_size,
        language=transcription_language,
        chunk_paths=chunk_paths if is_chunked else [],
    )
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, store: JobStore = Depends(get_job_store)):
    job = _get_job_or_404(job_id, store)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        transcript=job.transcript,
        detected_language=job.detected_language,
        summary=job.summary,
        error=job.error,
    )


@router.get("/{job_id}/stream")
async def stream_transcript(
    job_id: str,
    request: Request,
    chunk: int = 0,
    transcriber: Transcriber = Depends(get_transcriber),
    store: JobStore = Depends(get_job_store),
):
    """Streams the transcript to the client via Server-Sent Events as
    faster-whisper produces each segment.

    For long files the audio was split into chunks at upload time.  Each
    SSE connection processes exactly one chunk (selected by ?chunk=N) and
    then sends either:
      - "chunk_done" with the next chunk index  → frontend reconnects
      - "done"                                  → transcription complete
    This keeps each connection short enough to survive Azure's ingress
    timeout even for hour-long recordings.
    """
    job = _get_job_or_404(job_id, store)

    if job.status not in (JobStatus.QUEUED, JobStatus.TRANSCRIBING):
        raise HTTPException(
            status_code=409, detail=f"Job is '{job.status.value}', not ready to stream."
        )

    job.status = JobStatus.TRANSCRIBING
    store.save(job)

    chunks = job.chunk_paths
    if chunks:
        if chunk >= len(chunks):
            raise HTTPException(status_code=400, detail=f"Chunk index {chunk} out of range.")
        audio_path = chunks[chunk]
        is_last_chunk = chunk == len(chunks) - 1
    else:
        audio_path = job.audio_path
        is_last_chunk = True

    transcription_language = job.language or (job.detected_language if chunk > 0 else None)

    async def event_generator():
        async for kind, payload in stream_from_blocking_generator(
            lambda: transcriber.transcribe_stream(
                audio_path, beam_size=job.beam_size, language=transcription_language
            )
        ):
            client_gone = await request.is_disconnected()

            if kind is StreamEventKind.ITEM:
                if isinstance(payload, LanguageDetected):
                    if not job.detected_language:
                        job.detected_language = payload.language
                        store.save(job)
                    if not client_gone:
                        yield sse_event("language", payload.language)
                else:
                    segment_text = cast(str, payload)
                    job.transcript = ((job.transcript or "") + " " + segment_text).strip()
                    store.save(job)
                    if not client_gone:
                        yield sse_event("segment", segment_text)

            elif kind is StreamEventKind.DONE:
                if chunks:
                    with contextlib.suppress(OSError):
                        os.unlink(audio_path)

                if is_last_chunk:
                    full_transcript = (job.transcript or "").strip()
                    if not full_transcript:
                        job.status = JobStatus.ERROR
                        job.error = "No speech could be recognized in this file."
                        store.save(job)
                        if not client_gone:
                            yield sse_event("error", job.error)
                    else:
                        job.status = JobStatus.TRANSCRIBED
                        store.save(job)
                        with contextlib.suppress(OSError):
                            os.unlink(job.audio_path)
                        if not client_gone:
                            yield sse_event("done", full_transcript)
                        else:
                            logger.info(
                                "Job %s finished transcription after client disconnected; "
                                "result available via GET /api/jobs/%s",
                                job_id, job_id,
                            )
                else:
                    if not client_gone:
                        yield sse_event("chunk_done", str(chunk + 1))
                return

            elif kind is StreamEventKind.KEEPALIVE:
                if not client_gone:
                    yield ": keepalive\n\n"

            elif kind is StreamEventKind.ERROR:
                error = cast(BaseException, payload)
                logger.exception(
                    "Transcription failed for job %s chunk %d", job_id, chunk, exc_info=error
                )
                job.status = JobStatus.ERROR
                job.error = str(error)
                store.save(job)
                with contextlib.suppress(OSError):
                    os.unlink(job.audio_path)
                if not client_gone:
                    yield sse_event("error", str(error))
                return

            if client_gone:
                continue

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/{job_id}/summarize", response_model=SummaryResponse)
async def summarize_transcript(
    job_id: str,
    body: SummarizeRequest | None = None,
    summarizer: Summarizer = Depends(get_summarizer),
    store: JobStore = Depends(get_job_store),
):
    if body is None:
        body = SummarizeRequest()
    job = _get_job_or_404(job_id, store)
    if job.status != JobStatus.TRANSCRIBED or not job.transcript:
        raise HTTPException(
            status_code=409, detail=f"Job is '{job.status.value}', transcript not ready."
        )

    job.status = JobStatus.SUMMARIZING
    store.save(job)
    language = job.detected_language or "en"
    try:
        summary = await summarize_async(job.transcript, language, summarizer, body.summary_type)
    except SummarizationError as error:
        job.status = JobStatus.ERROR
        job.error = str(error)
        store.save(job)
        raise HTTPException(status_code=502, detail=str(error)) from error

    job.summary = summary
    job.status = JobStatus.DONE
    store.save(job)
    return SummaryResponse(job_id=job.id, status=job.status, summary=summary)


@router.get("/{job_id}/download/txt")
async def download_transcript_txt(job_id: str, store: JobStore = Depends(get_job_store)):
    job = _get_job_or_404(job_id, store)
    if not job.transcript:
        raise HTTPException(status_code=409, detail="Transcript not ready yet.")
    return Response(
        content=render_transcript_to_txt(job.transcript),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=transcript.txt"},
    )


@router.get("/{job_id}/download/docx")
async def download_summary_docx(job_id: str, store: JobStore = Depends(get_job_store)):
    job = _get_job_or_404(job_id, store)
    if not job.summary:
        raise HTTPException(status_code=409, detail="Summary not ready yet.")
    return Response(
        content=render_markdown_summary_to_docx(job.summary),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=summary.docx"},
    )
