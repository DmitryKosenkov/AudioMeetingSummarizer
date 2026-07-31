"""A Job tracks one uploaded audio file through the pipeline (upload ->
transcribe -> summarize). Stored in-memory; swap for Redis if this ever
needs to run across multiple processes.
"""
import threading
import uuid
from dataclasses import dataclass
from enum import Enum


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
    beam_size: int = 2
    language: str | None = None
    status: JobStatus = JobStatus.QUEUED
    transcript: str | None = None
    detected_language: str | None = None
    summary: str | None = None
    error: str | None = None
    chunk_paths: list[str] = None

    def __post_init__(self) -> None:
        if self.chunk_paths is None:
            self.chunk_paths = []


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job(
    filename: str,
    audio_path: str,
    beam_size: int = 2,
    language: str | None = None,
    chunk_paths: list[str] | None = None,
) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        filename=filename,
        audio_path=audio_path,
        beam_size=beam_size,
        language=language,
        chunk_paths=chunk_paths or [],
    )
    with _lock:
        _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)
