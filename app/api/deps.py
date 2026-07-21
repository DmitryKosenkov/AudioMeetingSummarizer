"""FastAPI dependency providers for the shared transcriber/summarizer
instances built once in app/main.py's lifespan and stored on app.state.
"""
from fastapi import Request

from app.services.summarizer import Summarizer
from app.services.transcriber import Transcriber


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


def get_summarizer(request: Request) -> Summarizer:
    return request.app.state.summarizer
