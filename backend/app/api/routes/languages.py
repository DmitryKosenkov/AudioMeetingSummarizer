"""Route exposing which languages the user can pick from on the upload
form, so the frontend doesn't need to hardcode its own copy of the list.
"""
from fastapi import APIRouter

from app.services.prompts import LANGUAGE_NAMES

router = APIRouter(tags=["languages"])

AUTO_DETECT = "auto"


@router.get("/languages")
async def list_languages():
    return {
        "default": AUTO_DETECT,
        "languages": [
            {"code": code, "name": name} for code, name in sorted(LANGUAGE_NAMES.items())
        ],
    }
