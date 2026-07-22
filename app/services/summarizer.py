import logging
import time
from abc import ABC, abstractmethod

from google import genai
from google.genai import errors as genai_errors

from app.services.prompts import build_meeting_summary_prompt

logger = logging.getLogger(__name__)

# Retry on transient server-side errors; fail fast on permanent ones (bad
# request, bad API key) since retrying those can't succeed.
RETRYABLE_STATUS_CODES = {429, 500, 503}


class SummarizationError(Exception):
    """Raised when a summary could not be produced."""


class Summarizer(ABC):
    """Turns a block of text into a short summary."""

    @abstractmethod
    def summarize(self, text: str, language: str) -> str:
        raise NotImplementedError


class GeminiSummarizer(Summarizer):
    """Summarization using Google Gemini, with retry on transient errors."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.1-flash-lite",
        max_attempts: int = 3,
        retry_delay_seconds: float = 5.0,
    ):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_attempts = max_attempts
        self.retry_delay_seconds = retry_delay_seconds

    def summarize(self, text: str, language: str) -> str:
        prompt = build_meeting_summary_prompt(text, language)
        response = self._generate_with_retry(prompt)

        if not response.text:
            logger.error("Gemini returned an empty response for prompt: %.200r", prompt)
            raise SummarizationError("Gemini returned an empty response.")

        return response.text

    def _generate_with_retry(self, prompt: str) -> "genai.types.GenerateContentResponse":
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.client.models.generate_content(model=self.model, contents=prompt)

            except genai_errors.APIError as e:
                last_error = e
                is_retryable = getattr(e, "code", None) in RETRYABLE_STATUS_CODES

                if not is_retryable or attempt == self.max_attempts:
                    logger.exception(
                        "Gemini request failed (attempt %s/%s, retryable=%s)",
                        attempt,
                        self.max_attempts,
                        is_retryable,
                    )
                    raise SummarizationError("Gemini request failed.") from None

                logger.warning(
                    "Gemini request failed (attempt %s/%s): %s. Retrying in %.0fs...",
                    attempt,
                    self.max_attempts,
                    e,
                    self.retry_delay_seconds * attempt,
                )
                time.sleep(self.retry_delay_seconds * attempt)

            except Exception:
                logger.exception("Gemini request failed with an unexpected error")
                raise SummarizationError("Gemini request failed.") from None

        raise SummarizationError("Gemini request failed.") from last_error
