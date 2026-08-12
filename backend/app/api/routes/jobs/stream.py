"""GET /api/jobs/{job_id}/stream — stream transcript segments via SSE.

Long files are split into chunks at upload time; each SSE connection
processes exactly one chunk (selected by ?chunk=N), then sends either:
  - "chunk_done" with the next index  → frontend reconnects
  - "done"                            → transcription complete

This keeps each connection short enough to survive Azure's ingress
timeout even for hour-long recordings.
"""
import contextlib
import logging
import os
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_job_store, get_transcriber
from app.api.routes.jobs.common import get_job_or_404
from app.models.job import JobStatus, JobStore
from app.services.transcriber import LanguageDetected, Transcriber
from app.utils.sse import sse_event
from app.utils.streaming import StreamEventKind, stream_from_blocking_generator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{job_id}/stream")
async def stream_transcript(
    job_id: str,
    request: Request,
    chunk: int = 0,
    transcriber: Transcriber = Depends(get_transcriber),
    store: JobStore = Depends(get_job_store),
):
    job = get_job_or_404(job_id, store)

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
