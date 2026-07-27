from fastapi import APIRouter

from app.api.routes import jobs

api_router = APIRouter(prefix="/api")
api_router.include_router(jobs.router)
