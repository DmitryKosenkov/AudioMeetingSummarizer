"""FastAPI dependency providers for the shared transcriber/summarizer/job-store
instances built once in app/main.py's lifespan and stored on app.state.
"""
from fastapi import Request

from app.models.job import JobStore
from app.services.summarizer import Summarizer
from app.services.transcriber import Transcriber


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


def get_summarizer(request: Request) -> Summarizer:
    return request.app.state.summarizer


def get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store
