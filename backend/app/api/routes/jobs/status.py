"""GET /api/jobs/{job_id} — return current job status."""
from fastapi import APIRouter, Depends

from app.api.deps import get_job_store
from app.api.routes.jobs.common import get_job_or_404
from app.models.job import JobStore
from app.schemas.job import JobStatusResponse

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, store: JobStore = Depends(get_job_store)):
    job = get_job_or_404(job_id, store)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        transcript=job.transcript,
        detected_language=job.detected_language,
        summary=job.summary,
        error=job.error,
    )
