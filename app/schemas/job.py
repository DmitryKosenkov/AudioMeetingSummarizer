"""Pydantic response models for the job endpoints."""
from typing import Optional

from pydantic import BaseModel

from app.models.job import JobStatus


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    transcript: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None


class SummaryResponse(BaseModel):
    job_id: str
    status: JobStatus
    summary: str
