
import json
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum


class JobStatus(str, Enum):
    QUEUED      = "queued"
    TRANSCRIBING = "transcribing"
    TRANSCRIBED = "transcribed"
    SUMMARIZING = "summarizing"
    DONE        = "done"
    ERROR       = "error"


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
    chunk_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        d = dict(d)
        d["status"] = JobStatus(d["status"])
        return cls(**d)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class JobStore(ABC):
    @abstractmethod
    def create(
        self,
        filename: str,
        audio_path: str,
        beam_size: int = 2,
        language: str | None = None,
        chunk_paths: list[str] | None = None,
    ) -> Job:
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: str) -> Job | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, job: Job) -> None:
        """Persist any mutations made to *job* since it was last loaded."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

class InMemoryJobStore(JobStore):

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(
        self,
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
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def save(self, job: Job) -> None:
        pass

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()


# ---------------------------------------------------------------------------
# Redis implementation
# ---------------------------------------------------------------------------

_JOB_TTL_SECONDS = 60 * 60 * 24


class RedisJobStore(JobStore):
    def __init__(self, redis_url: str) -> None:
        import redis as redis_lib
        self._redis = redis_lib.from_url(redis_url, decode_responses=True)

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def create(
        self,
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
        self.save(job)
        return job

    def get(self, job_id: str) -> Job | None:
        raw = self._redis.get(self._key(job_id))
        if raw is None:
            return None
        return Job.from_dict(json.loads(raw))

    def save(self, job: Job) -> None:
        self._redis.setex(
            self._key(job.id),
            _JOB_TTL_SECONDS,
            json.dumps(job.to_dict()),
        )
