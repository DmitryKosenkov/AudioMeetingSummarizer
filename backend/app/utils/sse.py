"""Server-Sent Events message formatting."""
import json
from typing import Any


def sse_event(event: str, data: Any) -> str:
    """Payload is JSON-encoded so it always stays on a single `data:` line."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
