"""Server-Sent Events (SSE) streaming endpoints.

Endpoints:
    GET /api/stream/fetch/{username}    — SSE stream for fetch progress
    GET /api/stream/analysis/{game_id}  — SSE stream for analysis progress

Requirements: 1.9, 5.5
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Callable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.progress_store import ProgressEntry, progress_store

router = APIRouter(prefix="/api/stream", tags=["streams"])


# ---------------------------------------------------------------------------
# SSE formatting helpers
# ---------------------------------------------------------------------------

def _sse_event(data: dict) -> str:
    """Format *data* as an SSE ``data:`` frame."""
    return f"data: {json.dumps(data)}\n\n"


def _sse_comment(text: str = "keepalive") -> str:
    """Format *text* as an SSE comment line (used for keep-alive)."""
    return f": {text}\n\n"


# ---------------------------------------------------------------------------
# Generic progress streamer
# ---------------------------------------------------------------------------

async def _stream_progress(
    entry: ProgressEntry | None,
    *,
    complete_payload_builder: Callable[[ProgressEntry], dict] | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE events for a :class:`ProgressEntry` until it completes.

    If *entry* is ``None`` an error event is emitted immediately.
    When the entry completes, a final ``complete`` (or ``error``) event
    is emitted and the generator returns.

    An optional *complete_payload_builder* can customise the final
    ``complete`` payload dict.
    """
    if entry is None:
        yield _sse_event({"type": "error", "message": "Progress entry not found"})
        return

    last_percentage: int | None = None

    while True:
        # Wait for the next signal from the producer
        await entry.event.wait()
        entry.event.clear()

        if entry.is_complete:
            if entry.error is not None:
                yield _sse_event({"type": "error", "message": entry.error})
            else:
                if complete_payload_builder is not None:
                    yield _sse_event(complete_payload_builder(entry))
                else:
                    payload: dict = {"type": "complete"}
                    if entry.result is not None:
                        payload["result"] = entry.result
                    yield _sse_event(payload)
            return

        # Emit progress only when the percentage actually changes
        pct = entry.percentage
        if pct != last_percentage:
            yield _sse_event({
                "type": "progress",
                "current": entry.current,
                "total": entry.total,
                "percentage": pct,
            })
            last_percentage = pct


# ---------------------------------------------------------------------------
# SSE endpoints
# ---------------------------------------------------------------------------

@router.get("/fetch/{username}")
async def stream_fetch_progress(username: str) -> StreamingResponse:
    """SSE stream for game-fetch progress."""
    entry = progress_store.get_fetch_entry(username)
    return StreamingResponse(
        _stream_progress(entry),
        media_type="text/event-stream",
    )


@router.get("/analysis/{game_id}")
async def stream_analysis_progress(game_id: str) -> StreamingResponse:
    """SSE stream for analysis progress."""
    entry = progress_store.get_analysis_entry(game_id)
    return StreamingResponse(
        _stream_progress(entry),
        media_type="text/event-stream",
    )
