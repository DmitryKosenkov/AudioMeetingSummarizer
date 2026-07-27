"""Application settings, loaded once from environment variables / .env."""
import os
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


@dataclass
class Settings:
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "small")
    whisper_language: str = os.getenv("WHISPER_LANGUAGE", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    gemini_max_attempts: int = int(os.getenv("GEMINI_MAX_ATTEMPTS", "3"))
    gemini_retry_delay_seconds: float = float(os.getenv("GEMINI_RETRY_DELAY_SECONDS", "5"))
    downloads_dir: str = os.getenv("DOWNLOADS_DIR", "downloads")


settings = Settings()
