from fastapi import APIRouter

from app.api.routes import jobs, languages

api_router = APIRouter(prefix="/api")
api_router.include_router(jobs.router)
api_router.include_router(languages.router)
