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

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.progress_store import progress_store

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
# Analysis SSE — polls _running_analyses from the analysis router
# ---------------------------------------------------------------------------

async def _stream_analysis(game_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE events by polling the analysis router's in-memory tracking.

    Falls back to checking the database for completed analyses.
    """
    # Import here to avoid circular imports
    from app.routers.analysis import _running_analyses
    from app.database import get_analysis_summary, get_connection

    last_percentage: int | None = None
    poll_interval = 1.0  # seconds

    while True:
        # Check in-memory tracking first (active analysis)
        if game_id in _running_analyses:
            status = _running_analyses[game_id]
            pct = status.percentage

            if status.is_complete:
                yield _sse_event({
                    "type": "complete",
                    "percentage": 100,
                    "is_complete": True,
                })
                return

            if pct != last_percentage:
                yield _sse_event({
                    "type": "progress",
                    "percentage": pct,
                    "is_complete": False,
                })
                last_percentage = pct
        else:
            # Not in memory — check if completed in DB
            try:
                conn = get_connection()
                summary = get_analysis_summary(conn, game_id)
                conn.close()
                if summary is not None and summary["is_complete"]:
                    yield _sse_event({
                        "type": "complete",
                        "percentage": 100,
                        "is_complete": True,
                    })
                    return
            except Exception:
                pass

            # Not running, not completed — might not have started yet.
            # Send a waiting event and keep polling (it may start soon).
            yield _sse_event({
                "type": "progress",
                "percentage": 0,
                "is_complete": False,
            })

        await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Fetch SSE — uses progress_store (unchanged)
# ---------------------------------------------------------------------------

async def _stream_fetch(username: str) -> AsyncGenerator[str, None]:
    """Yield SSE events for a fetch progress entry."""
    entry = progress_store.get_fetch_entry(username)
    if entry is None:
        yield _sse_event({"type": "complete", "percentage": 100})
        return

    last_percentage: int | None = None
    while True:
        await entry.event.wait()
        entry.event.clear()

        if entry.is_complete:
            if entry.error is not None:
                yield _sse_event({"type": "error", "message": entry.error})
            else:
                payload: dict = {"type": "complete"}
                if entry.result is not None:
                    payload["result"] = entry.result
                yield _sse_event(payload)
            return

        pct = entry.percentage
        if pct != last_percentage:
            yield _sse_event({
                "type": "progress",
                "percentage": pct,
            })
            last_percentage = pct


# ---------------------------------------------------------------------------
# SSE endpoints
# ---------------------------------------------------------------------------

@router.get("/fetch/{username}")
async def stream_fetch_progress(username: str) -> StreamingResponse:
    """SSE stream for game-fetch progress."""
    return StreamingResponse(
        _stream_fetch(username),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/analysis/{game_id}")
async def stream_analysis_progress(game_id: str) -> StreamingResponse:
    """SSE stream for analysis progress."""
    return StreamingResponse(
        _stream_analysis(game_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
