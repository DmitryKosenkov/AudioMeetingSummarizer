"""Transcriber is an abstract interface so the rest of the app doesn't
depend on faster-whisper specifically.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, Union

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LanguageDetected:
    """Yielded once, first, by transcribe_stream(): the language that was
    actually used for transcription - either the configured one, or the
    one faster-whisper auto-detected when none was configured.
    """

    language: str


class Transcriber(ABC):
    """Converts an audio file into text."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def transcribe_stream(self, audio_path: str) -> Iterator[Union[LanguageDetected, str]]:
        raise NotImplementedError


class WhisperTranscriber(Transcriber):
    """Local speech-to-text using faster-whisper."""

    def __init__(self, model_size: str = "large-v3-turbo", language: str = ""):
        logger.info("Loading Whisper model '%s'...", model_size)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        # Empty/unset means "not configured": None tells faster-whisper to
        # auto-detect the spoken language from the first ~30s of audio,
        # instead of assuming a fixed one.
        self.language = language or None
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: str) -> str:
        segments = [
            item for item in self.transcribe_stream(audio_path) if isinstance(item, str)
        ]
        return " ".join(segments).strip()

    def transcribe_stream(self, audio_path: str) -> Iterator[Union[LanguageDetected, str]]:
        try:
            segments, info = self.model.transcribe(
                audio_path, language=self.language, beam_size=5
            )
            yield LanguageDetected(info.language)
            for segment in segments:
                text = segment.text.strip()
                if text:
                    yield text
        except Exception:
            logger.exception("Whisper failed to process %s", audio_path)
            raise
