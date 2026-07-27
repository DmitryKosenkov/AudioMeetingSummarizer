"""FastAPI application instance.

Run via the project root's main.py (`python main.py`), not directly with
the uvicorn CLI - main.py sets reload_dirs so the reloader doesn't watch
.venv/downloads/etc.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.summarizer import GeminiSummarizer
from app.services.transcriber import WhisperTranscriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the transcriber/summarizer once at startup (loading the
    Whisper model is expensive) and store them on app.state.
    """
    setup_logging()

    app.state.transcriber = WhisperTranscriber(
        model_size=settings.whisper_model_size, language=settings.whisper_language
    )
    app.state.summarizer = GeminiSummarizer(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        max_attempts=settings.gemini_max_attempts,
        retry_delay_seconds=settings.gemini_retry_delay_seconds,
    )

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Audio Meeting Summarizer API", lifespan=lifespan)

    # Narrow allow_origins to your deployed frontend's URL before shipping.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
