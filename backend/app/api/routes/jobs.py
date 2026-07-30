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

from app.api.deps import get_summarizer, get_transcriber
from app.core.config import settings
from app.exporters.docx_export import render_markdown_summary_to_docx
from app.exporters.txt_export import render_transcript_to_txt
from app.models.job import Job, JobStatus, create_job, get_job
from app.schemas.job import JobCreateResponse, JobStatusResponse, SummaryResponse
from app.services.pipeline import summarize_async
from app.services.summarizer import SummarizationError, Summarizer
from app.services.transcriber import LanguageDetected, Transcriber
from app.utils.sse import sse_event
from app.utils.streaming import StreamEventKind, stream_from_blocking_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".opus", ".aac"}


def _get_job_or_404(job_id: str) -> Job:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("", response_model=JobCreateResponse)
async def upload_audio(file: UploadFile, beam_size: int = Form(default=2)):
    file_extension = os.path.splitext(file.filename or "")[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_extension}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    os.makedirs(settings.downloads_dir, exist_ok=True)
    saved_path = os.path.join(settings.downloads_dir, f"{uuid.uuid4()}{file_extension}")

    file_bytes = await file.read()

    def _write_to_disk() -> None:
        with open(saved_path, "wb") as saved_file:
            saved_file.write(file_bytes)

    await asyncio.to_thread(_write_to_disk)

    beam_size = max(1, min(beam_size, 5))  # clamp to valid faster-whisper range
    job = create_job(filename=file.filename or "audio", audio_path=saved_path, beam_size=beam_size)
    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = _get_job_or_404(job_id)
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
    transcriber: Transcriber = Depends(get_transcriber),
):
    """Streams the transcript to the client via Server-Sent Events as
    faster-whisper produces each segment. The background-thread/queue
    mechanics live in app/utils/streaming.py; this just reacts to each
    event as it arrives.
    """
    job = _get_job_or_404(job_id)
    if job.status != JobStatus.QUEUED:
        raise HTTPException(
            status_code=409, detail=f"Job is '{job.status.value}', not ready to stream."
        )

    job.status = JobStatus.TRANSCRIBING

    async def event_generator():
        transcript_pieces: list[str] = []
        disconnected = False

        async for kind, payload in stream_from_blocking_generator(
            lambda: transcriber.transcribe_stream(job.audio_path, beam_size=job.beam_size)
        ):
            if await request.is_disconnected():
                disconnected = True
                break

            if kind is StreamEventKind.ITEM:
                if isinstance(payload, LanguageDetected):
                    job.detected_language = payload.language
                    yield sse_event("language", payload.language)
                else:
                    segment_text = cast(str, payload)
                    transcript_pieces.append(segment_text)
                    yield sse_event("segment", segment_text)

            elif kind is StreamEventKind.DONE:
                full_transcript = " ".join(transcript_pieces).strip()
                if not full_transcript:
                    job.status = JobStatus.ERROR
                    job.error = "No speech could be recognized in this file."
                    yield sse_event("error", job.error)
                else:
                    job.transcript = full_transcript
                    job.status = JobStatus.TRANSCRIBED
                    with contextlib.suppress(OSError):
                        os.unlink(job.audio_path)
                    yield sse_event("done", full_transcript)

            elif kind is StreamEventKind.ERROR:
                error = cast(BaseException, payload)
                logger.exception("Transcription failed for job %s", job_id, exc_info=error)
                job.status = JobStatus.ERROR
                job.error = str(error)
                with contextlib.suppress(OSError):
                    os.unlink(job.audio_path)
                yield sse_event("error", str(error))

        if disconnected and job.status == JobStatus.TRANSCRIBING:
            job.status = JobStatus.QUEUED
            with contextlib.suppress(OSError):
                os.unlink(job.audio_path)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/{job_id}/summarize", response_model=SummaryResponse)
async def summarize_transcript(job_id: str, summarizer: Summarizer = Depends(get_summarizer)):
    job = _get_job_or_404(job_id)
    if job.status != JobStatus.TRANSCRIBED or not job.transcript:
        raise HTTPException(
            status_code=409, detail=f"Job is '{job.status.value}', transcript not ready."
        )

    job.status = JobStatus.SUMMARIZING
    language = job.detected_language or "en"
    try:
        summary = await summarize_async(job.transcript, language, summarizer)
    except SummarizationError as error:
        job.status = JobStatus.ERROR
        job.error = str(error)
        raise HTTPException(status_code=502, detail=str(error)) from error

    job.summary = summary
    job.status = JobStatus.DONE
    return SummaryResponse(job_id=job.id, status=job.status, summary=summary)


@router.get("/{job_id}/download/txt")
async def download_transcript_txt(job_id: str):
    job = _get_job_or_404(job_id)
    if not job.transcript:
        raise HTTPException(status_code=409, detail="Transcript not ready yet.")
    return Response(
        content=render_transcript_to_txt(job.transcript),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=transcript.txt"},
    )


@router.get("/{job_id}/download/docx")
async def download_summary_docx(job_id: str):
    job = _get_job_or_404(job_id)
    if not job.summary:
        raise HTTPException(status_code=409, detail="Summary not ready yet.")
    return Response(
        content=render_markdown_summary_to_docx(job.summary),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=summary.docx"},
    )
