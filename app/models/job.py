"""A Job tracks one uploaded audio file through the pipeline (upload ->
transcribe -> summarize). Stored in-memory; swap for Redis if this ever
needs to run across multiple processes.
"""
import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    QUEUED = "queued"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    SUMMARIZING = "summarizing"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    id: str
    filename: str
    audio_path: str
    status: JobStatus = JobStatus.QUEUED
    transcript: Optional[str] = None
    summary: Optional[str] = None
    error: Optional[str] = None


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job(filename: str, audio_path: str) -> Job:
    job = Job(id=str(uuid.uuid4()), filename=filename, audio_path=audio_path)
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    with _lock:
        return _jobs.get(job_id)
