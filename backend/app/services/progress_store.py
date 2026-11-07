"""In-memory progress store for SSE streaming.

Provides a shared store that the game-fetching and analysis endpoints
write to (via progress callbacks) and the SSE streaming endpoints read
from.  Uses :class:`asyncio.Event` to allow SSE generators to await
progress updates without polling.

Requirements: 1.9, 5.5
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProgressEntry:
    """A single progress tracker for a fetch or analysis operation.

    Attributes:
        current: Number of items processed so far.
        total: Total number of items to process.
        is_complete: Whether the operation has finished.
        result: Optional result payload sent on completion.
        error: Optional error message if the operation failed.
        event: An :class:`asyncio.Event` signaled on each update
            so that SSE generators can ``await`` changes.
    """

    current: int = 0
    total: int = 0
    is_complete: bool = False
    result: Any | None = None
    error: str | None = None
    event: asyncio.Event = field(default_factory=asyncio.Event)

    @property
    def percentage(self) -> int:
        """Return progress as a percentage (0–100)."""
        if self.total == 0:
            return 0
        return min(int((self.current / self.total) * 100), 100)

    def update(self, current: int, total: int) -> None:
        """Update progress and signal waiting consumers."""
        self.current = current
        self.total = total
        self.event.set()

    def complete(self, result: Any | None = None) -> None:
        """Mark the operation as complete and signal consumers."""
        self.is_complete = True
        self.result = result
        self.event.set()

    def fail(self, error: str) -> None:
        """Mark the operation as failed and signal consumers."""
        self.is_complete = True
        self.error = error
        self.event.set()


class ProgressStore:
    """Thread-safe in-memory store for operation progress.

    Keyed by a string identifier (username for fetches,
    game_id for analyses).  Each entry is a :class:`ProgressEntry`
    that SSE generators can await.
    """

    def __init__(self) -> None:
        self._fetch_entries: dict[str, ProgressEntry] = {}
        self._analysis_entries: dict[str, ProgressEntry] = {}

    # -- Fetch progress ----------------------------------------------------

    def create_fetch_entry(self, username: str) -> ProgressEntry:
        """Create or reset a fetch progress entry for *username*."""
        entry = ProgressEntry()
        self._fetch_entries[username] = entry
        return entry

    def get_fetch_entry(self, username: str) -> ProgressEntry | None:
        """Return the fetch progress entry for *username*, if any."""
        return self._fetch_entries.get(username)

    def remove_fetch_entry(self, username: str) -> None:
        """Remove the fetch progress entry for *username*."""
        self._fetch_entries.pop(username, None)

    # -- Analysis progress -------------------------------------------------

    def create_analysis_entry(self, game_id: str) -> ProgressEntry:
        """Create or reset an analysis progress entry for *game_id*."""
        entry = ProgressEntry()
        self._analysis_entries[game_id] = entry
        return entry

    def get_analysis_entry(self, game_id: str) -> ProgressEntry | None:
        """Return the analysis progress entry for *game_id*, if any."""
        return self._analysis_entries.get(game_id)

    def remove_analysis_entry(self, game_id: str) -> None:
        """Remove the analysis progress entry for *game_id*."""
        self._analysis_entries.pop(game_id, None)


# Module-level singleton so that routers and service endpoints share
# the same store instance.
progress_store = ProgressStore()
