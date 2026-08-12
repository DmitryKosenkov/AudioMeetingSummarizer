"""POST /api/jobs/{job_id}/summarize — summarize the transcript via Gemini."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_job_store, get_summarizer
from app.api.routes.jobs.common import get_job_or_404
from app.models.job import JobStatus, JobStore
from app.schemas.job import SummaryResponse
from app.services.pipeline import summarize_async
from app.services.prompts import SummaryType
from app.services.summarizer import SummarizationError, Summarizer

router = APIRouter()


class SummarizeRequest(BaseModel):
    summary_type: SummaryType = SummaryType.MEETING


@router.post("/{job_id}/summarize", response_model=SummaryResponse)
async def summarize_transcript(
    job_id: str,
    body: SummarizeRequest | None = None,
    summarizer: Summarizer = Depends(get_summarizer),
    store: JobStore = Depends(get_job_store),
):
    if body is None:
        body = SummarizeRequest()

    job = get_job_or_404(job_id, store)
    if job.status != JobStatus.TRANSCRIBED or not job.transcript:
        raise HTTPException(
            status_code=409, detail=f"Job is '{job.status.value}', transcript not ready."
        )

    job.status = JobStatus.SUMMARIZING
    store.save(job)
    try:
        summary = await summarize_async(
            job.transcript,
            job.detected_language or "en",
            summarizer,
            body.summary_type,
        )
    except SummarizationError as error:
        job.status = JobStatus.ERROR
        job.error = str(error)
        store.save(job)
        raise HTTPException(status_code=502, detail=str(error)) from error

    job.summary = summary
    job.status = JobStatus.DONE
    store.save(job)
    return SummaryResponse(job_id=job.id, status=job.status, summary=summary)
