"""Thin orchestration layer between routes and services, so routes don't
call summarizer.summarize() (a blocking call) directly.
"""
import asyncio

from app.services.summarizer import Summarizer


def summarize(text: str, summarizer: Summarizer) -> str:
    return summarizer.summarize(text)


async def summarize_async(text: str, summarizer: Summarizer) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, summarize, text, summarizer)
