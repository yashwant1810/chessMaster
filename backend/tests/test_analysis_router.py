"""Unit tests for the analysis router (backend/app/routers/analysis.py).

Tests three endpoints with an in-memory SQLite database:
- POST /api/analysis/{game_id}   — start analysis
- GET  /api/analysis/{game_id}   — get analysis results
- GET  /api/analysis/{game_id}/status — get analysis progress

Covers success paths, 404 / 409 error responses, and in-memory progress
tracking for running analyses.
"""

import json
import sqlite3
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import (
    SCHEMA_SQL,
    insert_analysis_result,
    insert_game,
    upsert_analysis_summary,
)
from app.models import AnalysisStatus, ParsedGame, PlayerAnalysisSummary
from app.routers.analysis import _get_db, _running_analyses, router


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_db():
    """Create an in-memory SQLite database with the schema initialised.

    ``check_same_thread=False`` is required because FastAPI's TestClient
    dispatches async endpoints in a separate thread.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def clear_running_analyses():
    """Ensure the in-memory analysis tracker is empty between tests."""
    _running_analyses.clear()
    yield
    _running_analyses.clear()


@pytest.fixture()
def client(in_memory_db):
    """FastAPI TestClient with the analysis router and overridden DB dep."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[_get_db] = lambda: in_memory_db

    with TestClient(app) as c:
        yield c


def _sample_game(**overrides) -> ParsedGame:
    defaults = dict(
        event="Live Chess",
        site="chess.com",
        date="2024.01.15",
        round="-",
        white="player1",
        black="player2",
        result="1-0",
        moves=["e4", "e5", "Nf3"],
        fens=["fen1", "fen2", "fen3"],
    )
    defaults.update(overrides)
    return ParsedGame(**defaults)


def _insert_sample_game(conn, game_id="game-1", **overrides) -> str:
    """Insert a sample game into the database and return its ID."""
    game = _sample_game(**overrides)
    insert_game(
        conn,
        game_id=game_id,
        username="testuser",
        pgn_raw='[Event "Live"]\n1. e4 e5 2. Nf3 1-0',
        game=game,
    )
    return game_id


def _insert_sample_analysis(conn, game_id="game-1") -> None:
    """Insert sample analysis results and summary for a game."""
    # Insert per-move analysis results.
    for i, (san, is_white) in enumerate(
        [("e4", True), ("e5", False), ("Nf3", True)]
    ):
        insert_analysis_result(
            conn=conn,
            game_id=game_id,
            move_index=i,
            is_white=is_white,
            move_san=san,
            fen_before=f"fen_before_{i}",
            fen_after=f"fen_after_{i}",
            eval_before=20 + i * 5,
            eval_after=15 + i * 5,
            classification="best" if i == 0 else "good",
            centipawn_loss=0 if i == 0 else 15,
            candidate_moves=[
                {"move_san": san, "evaluation": 20, "mate_in": None}
            ],
        )

    # Insert summary.
    white_summary = PlayerAnalysisSummary(
        best_count=1,
        excellent_count=0,
        good_count=1,
        inaccuracy_count=0,
        mistake_count=0,
        blunder_count=0,
        performance_ratings=[2800, 2750],
        final_performance_rating=2750,
    )
    black_summary = PlayerAnalysisSummary(
        best_count=0,
        excellent_count=0,
        good_count=1,
        inaccuracy_count=0,
        mistake_count=0,
        blunder_count=0,
        performance_ratings=[2600],
        final_performance_rating=2600,
    )
    upsert_analysis_summary(
        conn,
        game_id=game_id,
        is_complete=True,
        white_summary=white_summary,
        black_summary=black_summary,
    )


# ---------------------------------------------------------------------------
# POST /api/analysis/{game_id} — start analysis
# ---------------------------------------------------------------------------


class TestStartAnalysis:
    """Tests for POST /api/analysis/{game_id}."""

    @patch("app.routers.analysis._run_analysis_task")
    def test_success_returns_202(self, mock_task, client, in_memory_db):
        """Starting analysis for a valid game returns 202 Accepted."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.post("/api/analysis/game-1")

        assert resp.status_code == 202
        data = resp.json()
        assert data["game_id"] == "game-1"
        assert data["message"] == "Analysis started"
        assert data["total_positions"] == 3

    @patch("app.routers.analysis._run_analysis_task")
    def test_seeds_in_memory_tracking(self, mock_task, client, in_memory_db):
        """POST should seed _running_analyses before returning."""
        _insert_sample_game(in_memory_db, "game-1")

        client.post("/api/analysis/game-1")

        assert "game-1" in _running_analyses
        status = _running_analyses["game-1"]
        assert status.total_positions == 3
        assert status.positions_analyzed == 0
        assert status.is_complete is False

    def test_game_not_found_404(self, client):
        """Non-existent game → 404."""
        resp = client.post("/api/analysis/nonexistent")

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "game_not_found"

    @patch("app.routers.analysis._run_analysis_task")
    def test_conflict_409(self, mock_task, client, in_memory_db):
        """Starting analysis when already in progress → 409."""
        _insert_sample_game(in_memory_db, "game-1")
        # Simulate an already-running analysis.
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=3,
            positions_analyzed=1,
            is_complete=False,
        )

        resp = client.post("/api/analysis/game-1")

        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert detail["error"] == "analysis_in_progress"

    @patch("app.routers.analysis._run_analysis_task")
    def test_reanalysis_allowed(self, mock_task, client, in_memory_db):
        """Re-analysis is allowed when no analysis is currently running."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.post("/api/analysis/game-1")

        # Should succeed because analysis is complete (not in _running).
        assert resp.status_code == 202


# ---------------------------------------------------------------------------
# GET /api/analysis/{game_id} — get results
# ---------------------------------------------------------------------------


class TestGetAnalysisResults:
    """Tests for GET /api/analysis/{game_id}."""

    def test_returns_results(self, client, in_memory_db):
        """Completed analysis → 200 with full results."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == "game-1"
        assert data["is_complete"] is True
        assert len(data["moves"]) == 3
        assert data["white_summary"]["best_count"] == 1
        assert data["black_summary"]["good_count"] == 1
        assert data["white_summary"]["final_performance_rating"] == 2750
        assert data["black_summary"]["final_performance_rating"] == 2600

    def test_includes_evaluations(self, client, in_memory_db):
        """Response includes per-move evaluations for graph rendering."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1")

        data = resp.json()
        assert "evaluations" in data
        assert len(data["evaluations"]) == 3

    def test_not_analyzed_404(self, client, in_memory_db):
        """Game exists but not analyzed → 404."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1")

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "analysis_not_found"

    def test_no_game_404(self, client):
        """Nonexistent game → 404 (no analysis either)."""
        resp = client.get("/api/analysis/nonexistent")

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "analysis_not_found"


# ---------------------------------------------------------------------------
# GET /api/analysis/{game_id}/status — progress tracking
# ---------------------------------------------------------------------------


class TestGetAnalysisStatus:
    """Tests for GET /api/analysis/{game_id}/status."""

    def test_in_progress_from_memory(self, client):
        """In-progress analysis returns live progress from memory."""
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=10,
            positions_analyzed=5,
            is_complete=False,
        )

        resp = client.get("/api/analysis/game-1/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == "game-1"
        assert data["total_positions"] == 10
        assert data["positions_analyzed"] == 5
        assert data["percentage"] == 50
        assert data["is_complete"] is False

    def test_completed_from_db(self, client, in_memory_db):
        """Completed analysis falls back to DB for status."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1/status")

        assert resp.status_code == 200
        data = resp.json()
        assert data["game_id"] == "game-1"
        assert data["percentage"] == 100
        assert data["is_complete"] is True

    def test_no_analysis_404(self, client):
        """No analysis at all → 404."""
        resp = client.get("/api/analysis/nonexistent/status")

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "analysis_not_found"

    def test_zero_progress(self, client):
        """Analysis just started → 0% progress."""
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=20,
            positions_analyzed=0,
            is_complete=False,
        )

        resp = client.get("/api/analysis/game-1/status")

        data = resp.json()
        assert data["percentage"] == 0
        assert data["is_complete"] is False

    def test_memory_takes_priority_over_db(self, client, in_memory_db):
        """In-memory tracking takes priority over DB (stale) data."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        # Simulate a re-analysis in progress.
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=3,
            positions_analyzed=2,
            is_complete=False,
        )

        resp = client.get("/api/analysis/game-1/status")

        data = resp.json()
        # Should reflect the live in-memory state, not the DB.
        assert data["positions_analyzed"] == 2
        assert data["percentage"] == 66
        assert data["is_complete"] is False
