"""Shared pytest fixtures.

Tests never touch the real WhisperTranscriber or GeminiSummarizer - both
are expensive (a multi-GB model download; a real API key and network
call) and have no place running in CI. Instead we swap them out via
FastAPI's dependency_overrides, using tiny fake implementations of the
same Transcriber/Summarizer interfaces the app already depends on. This
is the whole reason those interfaces exist as abstract classes.
"""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_summarizer, get_transcriber
from app.main import app
from app.models import job as job_module
from app.services.summarizer import Summarizer
from app.services.transcriber import LanguageDetected, Transcriber


class FakeTranscriber(Transcriber):
    """Yields a fixed language + list of segments, or raises, on demand."""

    def __init__(self, segments=None, language="en", raise_error=False):
        self.segments = segments if segments is not None else ["Hello.", "This is a test."]
        self.language = language
        self.raise_error = raise_error
        self.requested_language = None

    def transcribe(self, audio_path: str, language: str | None = None) -> str:
        return " ".join(self.segments)

    def transcribe_stream(
        self, audio_path: str, beam_size: int = 2, language: str | None = None
    ) -> Iterator[LanguageDetected | str]:
        self.requested_language = language
        if self.raise_error:
            raise RuntimeError("simulated transcription failure")
        yield LanguageDetected(language or self.language)
        yield from self.segments


class FakeSummarizer(Summarizer):
    """Records the last (text, language) it was called with, for assertions."""

    def __init__(self, summary_text: str = "# Summary\n\nTest summary."):
        self.summary_text = summary_text
        self.last_call = None

    def summarize(self, text: str, language: str) -> str:
        self.last_call = (text, language)
        return self.summary_text


@pytest.fixture
def fake_transcriber():
    return FakeTranscriber()


@pytest.fixture
def fake_summarizer():
    return FakeSummarizer()


@pytest.fixture
def client(fake_transcriber, fake_summarizer):
    """A TestClient with the real Whisper/Gemini dependencies swapped for
    fakes. Deliberately NOT used as a context manager, so the app's real
    lifespan (which loads the Whisper model) never runs.
    """
    app.dependency_overrides[get_transcriber] = lambda: fake_transcriber
    app.dependency_overrides[get_summarizer] = lambda: fake_summarizer

    # The job store is a module-level dict, so it persists across tests
    # unless cleared here.
    job_module._jobs.clear()

    yield TestClient(app)

    app.dependency_overrides.clear()
    job_module._jobs.clear()


@pytest.fixture
def uploaded_job_id(client):
    """Uploads a small fake audio file and returns its job_id, QUEUED."""
    response = client.post(
        "/api/jobs",
        files={"file": ("meeting.mp3", b"fake audio bytes", "audio/mpeg")},
        data={"beam_size": 2},
    )
    assert response.status_code == 200
    return response.json()["job_id"]
