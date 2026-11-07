"""Tests for SSE streaming endpoints and progress store.

Covers the progress store mechanics (update, complete, fail, percentage)
and the SSE endpoints (/api/stream/fetch/{username},
/api/stream/analysis/{game_id}).

Requirements: 1.9, 5.5
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.services.progress_store import ProgressEntry, ProgressStore, progress_store
from app.routers.streams import _sse_event, _sse_comment, _stream_progress


# ---------------------------------------------------------------------------
# ProgressEntry unit tests
# ---------------------------------------------------------------------------

class TestProgressEntry:
    """Unit tests for the ProgressEntry dataclass."""

    def test_initial_state(self):
        entry = ProgressEntry()
        assert entry.current == 0
        assert entry.total == 0
        assert entry.is_complete is False
        assert entry.result is None
        assert entry.error is None
        assert entry.percentage == 0

    def test_percentage_calculation(self):
        entry = ProgressEntry(current=50, total=100)
        assert entry.percentage == 50

    def test_percentage_zero_total(self):
        entry = ProgressEntry(current=0, total=0)
        assert entry.percentage == 0

    def test_percentage_capped_at_100(self):
        entry = ProgressEntry(current=120, total=100)
        assert entry.percentage == 100

    def test_update_sets_values_and_signals_event(self):
        entry = ProgressEntry()
        entry.event.clear()
        entry.update(5, 10)
        assert entry.current == 5
        assert entry.total == 10
        assert entry.event.is_set()

    def test_complete_marks_done_and_signals_event(self):
        entry = ProgressEntry()
        entry.event.clear()
        entry.complete(result={"games_fetched": 42})
        assert entry.is_complete is True
        assert entry.result == {"games_fetched": 42}
        assert entry.event.is_set()

    def test_fail_marks_done_with_error(self):
        entry = ProgressEntry()
        entry.event.clear()
        entry.fail("Connection failed")
        assert entry.is_complete is True
        assert entry.error == "Connection failed"
        assert entry.event.is_set()


# ---------------------------------------------------------------------------
# ProgressStore unit tests
# ---------------------------------------------------------------------------

class TestProgressStore:
    """Unit tests for the ProgressStore singleton."""

    def test_fetch_entry_lifecycle(self):
        store = ProgressStore()
        entry = store.create_fetch_entry("testuser")
        assert store.get_fetch_entry("testuser") is entry
        store.remove_fetch_entry("testuser")
        assert store.get_fetch_entry("testuser") is None

    def test_analysis_entry_lifecycle(self):
        store = ProgressStore()
        entry = store.create_analysis_entry("game123")
        assert store.get_analysis_entry("game123") is entry
        store.remove_analysis_entry("game123")
        assert store.get_analysis_entry("game123") is None

    def test_get_nonexistent_returns_none(self):
        store = ProgressStore()
        assert store.get_fetch_entry("nonexistent") is None
        assert store.get_analysis_entry("nonexistent") is None

    def test_create_resets_entry(self):
        store = ProgressStore()
        entry1 = store.create_fetch_entry("user1")
        entry1.update(5, 10)
        entry2 = store.create_fetch_entry("user1")
        assert entry2.current == 0
        assert entry2.total == 0
        assert store.get_fetch_entry("user1") is entry2

    def test_remove_nonexistent_is_noop(self):
        store = ProgressStore()
        store.remove_fetch_entry("nope")  # Should not raise
        store.remove_analysis_entry("nope")  # Should not raise


# ---------------------------------------------------------------------------
# SSE format helpers
# ---------------------------------------------------------------------------

class TestSSEFormatting:
    """Unit tests for SSE event formatting functions."""

    def test_sse_event_format(self):
        result = _sse_event({"type": "progress", "percentage": 50})
        assert result == 'data: {"type": "progress", "percentage": 50}\n\n'

    def test_sse_event_parses_as_json(self):
        result = _sse_event({"type": "complete", "count": 100})
        # Strip 'data: ' prefix and trailing newlines
        json_str = result.removeprefix("data: ").strip()
        parsed = json.loads(json_str)
        assert parsed == {"type": "complete", "count": 100}

    def test_sse_comment_format(self):
        result = _sse_comment("keepalive")
        assert result == ": keepalive\n\n"

    def test_sse_comment_default(self):
        result = _sse_comment()
        assert result == ": keepalive\n\n"


# ---------------------------------------------------------------------------
# _stream_progress async generator tests
# ---------------------------------------------------------------------------

class TestStreamProgress:
    """Unit tests for the _stream_progress async generator."""

    @pytest.mark.asyncio
    async def test_none_entry_yields_error(self):
        events = []
        async for event in _stream_progress(None):
            events.append(event)
        assert len(events) == 1
        parsed = json.loads(events[0].removeprefix("data: ").strip())
        assert parsed["type"] == "error"
        assert "not found" in parsed["message"].lower()

    @pytest.mark.asyncio
    async def test_already_complete_yields_complete(self):
        entry = ProgressEntry(current=10, total=10, is_complete=True)
        entry.event.set()
        events = []
        async for event in _stream_progress(entry):
            events.append(event)
        # Should get the complete event
        assert len(events) >= 1
        last = json.loads(events[-1].removeprefix("data: ").strip())
        assert last["type"] == "complete"

    @pytest.mark.asyncio
    async def test_already_failed_yields_error(self):
        entry = ProgressEntry(is_complete=True, error="Timeout")
        entry.event.set()
        events = []
        async for event in _stream_progress(entry):
            events.append(event)
        assert len(events) >= 1
        last = json.loads(events[-1].removeprefix("data: ").strip())
        assert last["type"] == "error"
        assert last["message"] == "Timeout"

    @pytest.mark.asyncio
    async def test_progress_updates_streamed(self):
        entry = ProgressEntry()
        events: list[str] = []

        async def _simulate_progress():
            """Simulate progress updates from a background task."""
            await asyncio.sleep(0.05)
            entry.update(3, 10)
            await asyncio.sleep(0.05)
            entry.update(7, 10)
            await asyncio.sleep(0.05)
            entry.complete()

        task = asyncio.create_task(_simulate_progress())

        async for event in _stream_progress(entry):
            events.append(event)
            # Safety limit to prevent infinite loops in tests
            if len(events) > 20:
                break

        await task

        # We should have progress events and a complete event
        data_events = [
            json.loads(e.removeprefix("data: ").strip())
            for e in events
            if e.startswith("data:")
        ]

        types = [e["type"] for e in data_events]
        assert "progress" in types
        assert "complete" in types
        # Complete should be the last data event
        assert data_events[-1]["type"] == "complete"

    @pytest.mark.asyncio
    async def test_custom_complete_payload_builder(self):
        entry = ProgressEntry(is_complete=True, result={"games_fetched": 42})
        entry.event.set()

        def builder(e: ProgressEntry) -> dict:
            return {"type": "complete", "count": e.result["games_fetched"]}

        events = []
        async for event in _stream_progress(entry, complete_payload_builder=builder):
            events.append(event)

        last = json.loads(events[-1].removeprefix("data: ").strip())
        assert last == {"type": "complete", "count": 42}

    @pytest.mark.asyncio
    async def test_duplicate_percentage_not_emitted(self):
        """When percentage doesn't change, no duplicate progress events."""
        entry = ProgressEntry()
        events: list[str] = []

        async def _simulate():
            await asyncio.sleep(0.05)
            entry.update(1, 10)  # 10%
            await asyncio.sleep(0.05)
            entry.update(1, 10)  # Still 10% — should not duplicate
            await asyncio.sleep(0.05)
            entry.complete()

        task = asyncio.create_task(_simulate())

        async for event in _stream_progress(entry):
            events.append(event)
            if len(events) > 20:
                break

        await task

        progress_events = [
            json.loads(e.removeprefix("data: ").strip())
            for e in events
            if e.startswith("data:") and "progress" in e
        ]
        # All progress events should be the same percentage (10%)
        percentages = [e["percentage"] for e in progress_events if e["type"] == "progress"]
        # Should only have at most one 10% progress event (plus the initial 0%)
        assert len(percentages) <= 2  # 0% initial + 10% update


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

class TestModuleSingleton:
    """Verify the module-level progress_store singleton exists."""

    def test_singleton_is_progress_store(self):
        assert isinstance(progress_store, ProgressStore)
