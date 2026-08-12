"""Job routes sub-package.

Each module handles exactly one part of the job lifecycle:

    upload.py    POST /jobs                      create a job from an audio file
    status.py    GET  /jobs/{id}                 poll current state
    stream.py    GET  /jobs/{id}/stream          live SSE transcript stream
    summarize.py POST /jobs/{id}/summarize       generate summary via Gemini
    download.py  GET  /jobs/{id}/download/txt|docx
"""
from fastapi import APIRouter

from app.api.routes.jobs import download, status, stream, summarize
from app.api.routes.jobs.upload import upload_audio

router = APIRouter(prefix="/jobs", tags=["jobs"])

# upload_audio uses an empty path ("") which FastAPI forbids when nesting
# via include_router — both the include prefix and route path would be empty.
# Adding the route directly lets FastAPI see the full path as /jobs.
router.add_api_route(
    "",
    upload_audio,
    methods=["POST"],
    response_model=None,
    summary="Upload audio",
)

router.include_router(status.router)
router.include_router(stream.router)
router.include_router(summarize.router)
router.include_router(download.router)
