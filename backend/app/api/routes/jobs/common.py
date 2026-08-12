"""Shared helpers for job route modules."""
from fastapi import HTTPException

from app.models.job import Job, JobStore

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".webm", ".opus", ".aac"}


def get_job_or_404(job_id: str, store: JobStore) -> Job:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
