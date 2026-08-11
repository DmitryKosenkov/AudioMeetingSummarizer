"""FastAPI application instance.

Run via the project root's main.py (`python main.py`), not directly with
the uvicorn CLI - main.py sets reload_dirs so the reloader doesn't watch
.venv/downloads/etc.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.models.job import InMemoryJobStore, RedisJobStore
from app.services.summarizer import GeminiSummarizer
from app.services.transcriber import WhisperTranscriber

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    if settings.redis_url:
        logger.info("Using Redis job store: %s", settings.redis_url)
        app.state.job_store = RedisJobStore(settings.redis_url)
    else:
        logger.info("REDIS_URL not set — using in-memory job store.")
        app.state.job_store = InMemoryJobStore()

    app.state.transcriber = WhisperTranscriber(model_size=settings.whisper_model_size)
    app.state.summarizer = GeminiSummarizer(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        max_attempts=settings.gemini_max_attempts,
        retry_delay_seconds=settings.gemini_retry_delay_seconds,
    )

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Audio Meeting Summarizer API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
