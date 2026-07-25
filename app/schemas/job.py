"""Pydantic response models for the job endpoints."""
from pydantic import BaseModel

from app.models.job import JobStatus


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    transcript: str | None = None
    detected_language: str | None = None
    summary: str | None = None
    error: str | None = None


class SummaryResponse(BaseModel):
    job_id: str
    status: JobStatus
    summary: str
