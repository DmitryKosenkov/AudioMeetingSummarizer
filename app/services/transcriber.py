"""Transcriber is an abstract interface so the rest of the app doesn't
depend on faster-whisper specifically.
"""
import logging
from abc import ABC, abstractmethod
from typing import Iterator

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class Transcriber(ABC):
    """Converts an audio file into text."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def transcribe_stream(self, audio_path: str) -> Iterator[str]:
        """Yield transcript segments as they become available."""
        raise NotImplementedError


class WhisperTranscriber(Transcriber):
    """Local speech-to-text using faster-whisper."""

    def __init__(self, model_size: str = "large-v3-turbo", language: str = "ru"):
        logger.info("Loading Whisper model '%s'...", model_size)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = language
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: str) -> str:
        return " ".join(self.transcribe_stream(audio_path)).strip()

    def transcribe_stream(self, audio_path: str) -> Iterator[str]:
        """Yield each segment's text as faster-whisper produces it.

        faster-whisper's `.transcribe()` returns a generator that decodes
        the audio incrementally, so segments really do become available
        one at a time rather than all at once at the end.
        """
        try:
            segments, _info = self.model.transcribe(
                audio_path, language=self.language, beam_size=5
            )
            for segment in segments:
                text = segment.text.strip()
                if text:
                    yield text
        except Exception:
            logger.exception("Whisper failed to process %s", audio_path)
            raise
