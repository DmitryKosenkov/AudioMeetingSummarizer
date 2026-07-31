"""Transcriber is an abstract interface so the rest of the app doesn't
depend on faster-whisper specifically.
"""
import logging
import math
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

_TARGET_CHUNK_MINUTES = 10
_MIN_CHUNK_SECONDS = 300   # 5 min — don't bother chunking tiny files
_MAX_CHUNK_SECONDS = 600   # 10 min hard ceiling


def _chunk_length_for(duration_seconds: float) -> int | None:
    if duration_seconds <= _MIN_CHUNK_SECONDS:
        return None
    num_chunks = math.ceil(duration_seconds / (_TARGET_CHUNK_MINUTES * 60))
    chunk = math.ceil(duration_seconds / num_chunks)
    return min(chunk, _MAX_CHUNK_SECONDS)


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
    def transcribe(self, audio_path: str, language: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def transcribe_stream(
        self, audio_path: str, beam_size: int = 2, language: str | None = None
    ) -> Iterator[LanguageDetected | str]:
        raise NotImplementedError


class WhisperTranscriber(Transcriber):
    def __init__(self, model_size: str = "small"):
        logger.info("Loading Whisper model '%s'...", model_size)
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
        )
        logger.info("Whisper model loaded.")

    def transcribe(self, audio_path: str, language: str | None = None) -> str:
        segments = [
            item
            for item in self.transcribe_stream(audio_path, language=language)
            if isinstance(item, str)
        ]
        return " ".join(segments).strip()

    def transcribe_stream(
        self, audio_path: str, beam_size: int = 2, language: str | None = None
    ) -> Iterator[LanguageDetected | str]:
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language or None,
                beam_size=beam_size,
            )

            chunk_length = _chunk_length_for(info.duration)
            if chunk_length is not None:
                logger.info(
                    "Audio duration %.0fs — re-transcribing with chunk_length=%ds (%d chunks)",
                    info.duration,
                    chunk_length,
                    math.ceil(info.duration / chunk_length),
                )
                segments, info = self.model.transcribe(
                    audio_path,
                    language=info.language,
                    beam_size=beam_size,
                    chunk_length=chunk_length,
                )

            yield LanguageDetected(info.language)
            for segment in segments:
                text = segment.text.strip()
                if text:
                    yield text
        except Exception:
            logger.exception("Whisper failed to process %s", audio_path)
            raise
