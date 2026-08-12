"""GET /api/jobs/{job_id}/download/txt|docx — download transcript and summary."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.deps import get_job_store
from app.api.routes.jobs.common import get_job_or_404
from app.exporters.docx_export import render_markdown_summary_to_docx
from app.exporters.txt_export import render_transcript_to_txt
from app.models.job import JobStore

router = APIRouter()


@router.get("/{job_id}/download/txt")
async def download_transcript_txt(job_id: str, store: JobStore = Depends(get_job_store)):
    job = get_job_or_404(job_id, store)
    if not job.transcript:
        raise HTTPException(status_code=409, detail="Transcript not ready yet.")
    return Response(
        content=render_transcript_to_txt(job.transcript),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=transcript.txt"},
    )


@router.get("/{job_id}/download/docx")
async def download_summary_docx(job_id: str, store: JobStore = Depends(get_job_store)):
    job = get_job_or_404(job_id, store)
    if not job.summary:
        raise HTTPException(status_code=409, detail="Summary not ready yet.")
    return Response(
        content=render_markdown_summary_to_docx(job.summary),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=summary.docx"},
    )
