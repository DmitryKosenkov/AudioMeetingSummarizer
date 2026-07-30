"""Bridges a synchronous (blocking) generator into an async iterator, so
it can be consumed inside a FastAPI route without blocking the event loop.

The generator runs on a background thread; each item it produces is handed
back to the event loop via `loop.call_soon_threadsafe` and placed on an
asyncio.Queue, which is then drained here.
"""
import asyncio
import threading
import time
from collections.abc import AsyncIterator, Callable, Iterator
from enum import Enum
from typing import Any

_HEARTBEAT_INTERVAL = 10.0  # seconds


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
    or ERROR. HEARTBEAT tuples are interleaved periodically to keep the SSE
    connection alive during long silent phases (e.g. VAD preprocessing).
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    done = threading.Event()

    def heartbeat_thread() -> None:
        """Send a heartbeat every _HEARTBEAT_INTERVAL seconds until the
        generator finishes. Runs independently of the generator thread so
        heartbeats fire even when the generator is blocked inside a long
        synchronous call (e.g. faster-whisper's VAD preprocessing step,
        which runs before the segment iterator yields anything at all).
        """
        while not done.wait(timeout=_HEARTBEAT_INTERVAL):
            loop.call_soon_threadsafe(
                queue.put_nowait, (StreamEventKind.HEARTBEAT, None)
            )

    def generator_thread() -> None:
        try:
            for item in make_generator():
                loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.ITEM, item))
            loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.DONE, None))
        except Exception as error:  # noqa: BLE001
            loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.ERROR, error))
        finally:
            done.set()

    loop.call_soon_threadsafe(queue.put_nowait, (StreamEventKind.HEARTBEAT, None))

    threading.Thread(target=heartbeat_thread, daemon=True).start()
    threading.Thread(target=generator_thread, daemon=True).start()

    while True:
        kind, payload = await queue.get()
        yield kind, payload
        if kind in (StreamEventKind.DONE, StreamEventKind.ERROR):
            return
