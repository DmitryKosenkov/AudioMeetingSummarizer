"""Bridges a synchronous (blocking) generator into an async iterator, so
it can be consumed inside a FastAPI route without blocking the event loop.

The generator runs on a background thread; each item it produces is handed
back to the event loop via `loop.call_soon_threadsafe` and placed on an
asyncio.Queue, which is then drained here.

A periodic heartbeat is sent while the queue is idle so that Azure Container
Apps' 240-second connection timeout doesn't drop the SSE stream mid-transcription.
"""
import asyncio
import threading
from collections.abc import AsyncIterator, Callable, Iterator
from enum import Enum
from typing import Any

_HEARTBEAT_INTERVAL = 20.0  # seconds


class StreamEventKind(str, Enum):
    ITEM = "item"
    DONE = "done"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


async def stream_from_blocking_generator(
    make_generator: Callable[[], Iterator[Any]],
) -> AsyncIterator[tuple[StreamEventKind, Any]]:
    """Run a blocking generator on a background thread and yield its items
    as (StreamEventKind, payload) tuples: ITEM per item, then a final DONE
    or ERROR. HEARTBEAT tuples are interleaved whenever the queue is idle for
    longer than _HEARTBEAT_INTERVAL seconds.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def run_on_background_thread() -> None:
        try:
            for item in make_generator():
                loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.ITEM, item))
            loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.DONE, None))
        except Exception as error:  # noqa: BLE001 - report it to the client instead of crashing the thread
            loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.ERROR, error))

    threading.Thread(target=run_on_background_thread, daemon=True).start()

    while True:
        try:
            kind, payload = await asyncio.wait_for(
                queue.get(), timeout=_HEARTBEAT_INTERVAL
            )
        except TimeoutError:
            yield StreamEventKind.HEARTBEAT, None
            continue

        yield kind, payload
        if kind in (StreamEventKind.DONE, StreamEventKind.ERROR):
            return
