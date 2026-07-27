"""Thin orchestration layer between routes and services, so routes don't
call summarizer.summarize() (a blocking call) directly.
"""
import asyncio

from app.services.summarizer import Summarizer


def summarize(text: str, language: str, summarizer: Summarizer) -> str:
    return summarizer.summarize(text, language)


async def summarize_async(text: str, language: str, summarizer: Summarizer) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, summarize, text, language, summarizer)
