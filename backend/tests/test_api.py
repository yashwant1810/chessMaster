"""Integration tests for the Chess Review Engine API.

Tests the full FastAPI application (``app.main.app``) through
:class:`~fastapi.testclient.TestClient`, exercising routes + middleware +
error handlers together.

Unlike the individual router tests (``test_games_router.py``,
``test_analysis_router.py``) and middleware tests (``test_middleware.py``),
these tests verify that the complete application stack works end-to-end:
requests pass through CORS middleware, global exception handlers, and
the actual route handlers in a single call path.

Requirements: 1.5, 1.6, 1.8, 2.3, 2.4, 2.5
"""

import sqlite3
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.database import (
    SCHEMA_SQL,
    insert_analysis_result,
    insert_game,
    upsert_analysis_summary,
)
from app.main import app
from app.models import AnalysisStatus, FetchResult, ParsedGame, PlayerAnalysisSummary
from app.routers.analysis import _get_db as analysis_get_db
from app.routers.analysis import _running_analyses
from app.routers.games import _get_db as games_get_db
from app.routers.games import _get_game_fetcher
from app.services.chess_api_client import (
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.game_fetcher import GameFetcher
from app.services.pgn_parser import PGNParseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_game(**overrides) -> ParsedGame:
    """Build a ParsedGame with sensible defaults."""
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
    """Insert a sample game and return its ID."""
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
    upsert_analysis_summary(
        conn,
        game_id=game_id,
        is_complete=True,
        white_summary=PlayerAnalysisSummary(
            best_count=1, excellent_count=0, good_count=1,
            inaccuracy_count=0, mistake_count=0, blunder_count=0,
            performance_ratings=[2800, 2750],
            final_performance_rating=2750,
        ),
        black_summary=PlayerAnalysisSummary(
            best_count=0, excellent_count=0, good_count=1,
            inaccuracy_count=0, mistake_count=0, blunder_count=0,
            performance_ratings=[2600],
            final_performance_rating=2600,
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_db():
    """In-memory SQLite database with schema initialised."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def mock_fetcher():
    """AsyncMock standing in for GameFetcher."""
    return AsyncMock(spec=GameFetcher)


@pytest.fixture(autouse=True)
def _clear_running_analyses():
    """Ensure the in-memory analysis tracker is clean between tests."""
    _running_analyses.clear()
    yield
    _running_analyses.clear()


@pytest.fixture()
def client(in_memory_db, mock_fetcher):
    """TestClient wired to the *real* app with overridden dependencies.

    Uses the actual ``app`` from ``app.main`` so that all routers,
    middleware, CORS, and global exception handlers are active.
    """
    app.dependency_overrides[games_get_db] = lambda: in_memory_db
    app.dependency_overrides[analysis_get_db] = lambda: in_memory_db
    app.dependency_overrides[_get_game_fetcher] = lambda: mock_fetcher

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ===================================================================
# Health check — basic wiring sanity
# ===================================================================


class TestHealthCheck:
    """GET /health verifies the full app starts and responds."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


# ===================================================================
# Game fetch endpoints (routes + middleware + error handlers)
# ===================================================================


class TestFetchProfileIntegration:
    """POST /api/games/fetch-profile through the full application stack."""

    def test_valid_username_returns_200(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Successful profile fetch returns game count. (Req 1.1)"""
        mock_fetcher.fetch_profile_games.return_value = FetchResult(
            username="hikaru",
            games_fetched=42,
            is_capped=False,
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "hikaru"
        assert body["games_fetched"] == 42
        assert body["is_capped"] is False

    def test_invalid_username_returns_400(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Empty username → 400 with invalid_username error. (Req 1.6)"""
        mock_fetcher.fetch_profile_games.side_effect = ValueError(
            "Username must be 1-25 characters"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": ""}
        )

        assert resp.status_code == 400
        body = resp.json()
        # Full-app response: error is in "detail" when raised as HTTPException
        detail = body.get("detail", body)
        assert detail["error"] == "invalid_username"
        assert "1-25 characters" in detail["message"]

    def test_username_not_found_returns_404(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Non-existent chess.com username → 404. (Req 1.8)"""
        mock_fetcher.fetch_profile_games.side_effect = UsernameNotFoundError(
            "nonexistent"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "nonexistent"}
        )

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "username_not_found"

    def test_timeout_returns_504(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """chess.com timeout → 504 upstream_timeout. (Req 1.5)"""
        cause = httpx.ReadTimeout("timed out")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_profile_games.side_effect = exc

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 504
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "upstream_timeout"
        assert "chess.com" in detail["message"]

    def test_unreachable_returns_502(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """chess.com network error → 502 upstream_unreachable."""
        cause = httpx.ConnectError("connection refused")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_profile_games.side_effect = exc

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 502
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "upstream_unreachable"

    def test_no_games_found_returns_200_with_message(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Username exists but no games → 200 with zero count. (Req 1.7)"""
        mock_fetcher.fetch_profile_games.return_value = FetchResult(
            username="newplayer",
            games_fetched=0,
            is_capped=False,
            message="No games found for this username",
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "newplayer"}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["games_fetched"] == 0
        assert "No games found" in body["message"]


class TestFetchURLIntegration:
    """POST /api/games/fetch-url through the full application stack."""

    VALID_URL = "https://www.chess.com/game/live/12345"

    def test_valid_url_returns_200(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Successful single-game fetch returns confirmation. (Req 2.6)"""
        mock_fetcher.fetch_game_by_url.return_value = FetchResult(
            username="player1",
            games_fetched=1,
            is_capped=False,
            message="Game loaded and available for analysis",
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["games_fetched"] == 1
        assert "Game loaded" in body["message"]

    def test_invalid_url_returns_400(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Invalid URL format → 400 with invalid_url error. (Req 2.3)"""
        mock_fetcher.fetch_game_by_url.side_effect = ValueError(
            "Not a valid chess.com game URL"
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": "https://example.com"}
        )

        assert resp.status_code == 400
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "invalid_url"

    def test_game_not_found_returns_404(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """Non-existent game → 404. (Req 2.4)"""
        mock_fetcher.fetch_game_by_url.side_effect = GameNotFoundError(
            self.VALID_URL
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "game_not_found"

    def test_timeout_returns_504(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """chess.com timeout during URL fetch → 504. (Req 2.5)"""
        cause = httpx.ReadTimeout("timed out")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_game_by_url.side_effect = exc

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 504
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "upstream_timeout"

    def test_pgn_parse_error_returns_422(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """PGN parsing failure after retrieval → 422."""
        mock_fetcher.fetch_game_by_url.side_effect = PGNParseError(
            "Parsing failed at move 3: illegal move"
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 422
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "pgn_parse_error"


# ===================================================================
# Game list endpoints (routes + middleware)
# ===================================================================


class TestGameListIntegration:
    """GET /api/games and GET /api/games/{game_id} through the full stack."""

    def test_empty_list(self, client: TestClient) -> None:
        """No games fetched → empty list. (Req 3.5)"""
        resp = client.get("/api/games")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_inserted_games(
        self, client: TestClient, in_memory_db
    ) -> None:
        """Returns all stored games."""
        _insert_sample_game(in_memory_db, "game-1", date="2024.01.15")
        _insert_sample_game(in_memory_db, "game-2", date="2024.06.20")

        resp = client.get("/api/games")

        assert resp.status_code == 200
        games = resp.json()
        assert len(games) == 2

    def test_default_sort_is_date_desc(
        self, client: TestClient, in_memory_db
    ) -> None:
        """Default sort: most recent first. (Req 3.1)"""
        _insert_sample_game(in_memory_db, "old", date="2023.01.01")
        _insert_sample_game(in_memory_db, "new", date="2024.06.15")

        resp = client.get("/api/games")

        games = resp.json()
        assert games[0]["id"] == "new"
        assert games[1]["id"] == "old"

    def test_get_game_by_id(
        self, client: TestClient, in_memory_db
    ) -> None:
        """GET /api/games/{game_id} returns game details."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.get("/api/games/game-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "game-1"
        assert body["white"] == "player1"

    def test_get_nonexistent_game_returns_404(
        self, client: TestClient
    ) -> None:
        """Non-existent game_id → 404."""
        resp = client.get("/api/games/nonexistent")

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "game_not_found"


# ===================================================================
# Analysis endpoints (routes + middleware + error handlers)
# ===================================================================


class TestAnalysisIntegration:
    """Analysis endpoints through the full application stack."""

    @patch("app.routers.analysis._run_analysis_task")
    def test_start_analysis_returns_202(
        self, mock_task, client: TestClient, in_memory_db
    ) -> None:
        """Starting analysis for a valid game → 202 Accepted."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.post("/api/analysis/game-1")

        assert resp.status_code == 202
        body = resp.json()
        assert body["game_id"] == "game-1"
        assert body["message"] == "Analysis started"
        assert body["total_positions"] == 3

    @patch("app.routers.analysis._run_analysis_task")
    def test_start_analysis_conflict_returns_409(
        self, mock_task, client: TestClient, in_memory_db
    ) -> None:
        """Starting analysis when already running → 409 conflict."""
        _insert_sample_game(in_memory_db, "game-1")
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=3,
            positions_analyzed=1,
            is_complete=False,
        )

        resp = client.post("/api/analysis/game-1")

        assert resp.status_code == 409
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "analysis_in_progress"
        assert "already running" in detail["message"]

    def test_start_analysis_game_not_found_returns_404(
        self, client: TestClient
    ) -> None:
        """Starting analysis for non-existent game → 404."""
        resp = client.post("/api/analysis/nonexistent")

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "game_not_found"

    def test_get_results_returns_complete_analysis(
        self, client: TestClient, in_memory_db
    ) -> None:
        """GET /api/analysis/{game_id} with completed analysis → 200."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["game_id"] == "game-1"
        assert body["is_complete"] is True
        assert len(body["moves"]) == 3
        assert "white_summary" in body
        assert "black_summary" in body
        assert "evaluations" in body
        assert body["white_summary"]["best_count"] == 1
        assert body["black_summary"]["final_performance_rating"] == 2600

    def test_get_results_not_analyzed_returns_404(
        self, client: TestClient, in_memory_db
    ) -> None:
        """GET results for un-analyzed game → 404 analysis_not_found."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1")

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "analysis_not_found"
        assert "Run analysis first" in detail["message"]

    def test_get_status_in_progress(self, client: TestClient) -> None:
        """GET status for in-progress analysis → 200 with progress."""
        _running_analyses["game-1"] = AnalysisStatus(
            game_id="game-1",
            total_positions=10,
            positions_analyzed=5,
            is_complete=False,
        )

        resp = client.get("/api/analysis/game-1/status")

        assert resp.status_code == 200
        body = resp.json()
        assert body["game_id"] == "game-1"
        assert body["percentage"] == 50
        assert body["is_complete"] is False

    def test_get_status_completed(
        self, client: TestClient, in_memory_db
    ) -> None:
        """GET status for completed analysis → 200 with 100%."""
        _insert_sample_game(in_memory_db, "game-1")
        _insert_sample_analysis(in_memory_db, "game-1")

        resp = client.get("/api/analysis/game-1/status")

        assert resp.status_code == 200
        body = resp.json()
        assert body["percentage"] == 100
        assert body["is_complete"] is True

    def test_get_status_no_analysis_returns_404(
        self, client: TestClient
    ) -> None:
        """GET status when no analysis exists → 404."""
        resp = client.get("/api/analysis/nonexistent/status")

        assert resp.status_code == 404
        body = resp.json()
        detail = body.get("detail", body)
        assert detail["error"] == "analysis_not_found"


# ===================================================================
# Error response shape consistency across the full stack
# ===================================================================


class TestErrorResponseShape:
    """Every error response contains ``error`` and ``message`` keys.

    Verifies that error responses maintain a consistent shape when
    flowing through both routers and global exception handlers.
    """

    def test_invalid_username_has_error_and_message(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """400 from invalid username has correct shape. (Req 1.6)"""
        mock_fetcher.fetch_profile_games.side_effect = ValueError(
            "Username must be 1-25 characters"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": ""}
        )

        assert resp.status_code == 400
        detail = resp.json().get("detail", resp.json())
        assert isinstance(detail["error"], str)
        assert isinstance(detail["message"], str)

    def test_invalid_url_has_error_and_message(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """400 from invalid URL has correct shape. (Req 2.3)"""
        mock_fetcher.fetch_game_by_url.side_effect = ValueError(
            "Not a valid chess.com game URL"
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": "bad"}
        )

        assert resp.status_code == 400
        detail = resp.json().get("detail", resp.json())
        assert isinstance(detail["error"], str)
        assert isinstance(detail["message"], str)

    def test_not_found_has_error_and_message(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """404 from username-not-found has correct shape. (Req 1.8)"""
        mock_fetcher.fetch_profile_games.side_effect = UsernameNotFoundError(
            "ghost"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "ghost"}
        )

        assert resp.status_code == 404
        detail = resp.json().get("detail", resp.json())
        assert "error" in detail
        assert "message" in detail

    def test_timeout_has_error_and_message(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """504 from timeout has correct shape. (Req 1.5)"""
        cause = httpx.ReadTimeout("timed out")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_profile_games.side_effect = exc

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 504
        detail = resp.json().get("detail", resp.json())
        assert "error" in detail
        assert "message" in detail

    def test_game_not_found_has_error_and_message(
        self, client: TestClient
    ) -> None:
        """404 from nonexistent game_id has correct shape."""
        resp = client.get("/api/games/nonexistent")

        assert resp.status_code == 404
        detail = resp.json().get("detail", resp.json())
        assert "error" in detail
        assert "message" in detail

    def test_analysis_not_found_has_error_and_message(
        self, client: TestClient
    ) -> None:
        """404 from un-analyzed game has correct shape."""
        resp = client.get("/api/analysis/nonexistent")

        assert resp.status_code == 404
        detail = resp.json().get("detail", resp.json())
        assert "error" in detail
        assert "message" in detail


# ===================================================================
# CORS integration — headers present on real route responses
# ===================================================================


class TestCORSIntegration:
    """CORS headers appear on responses from actual API routes."""

    def test_cors_header_on_success(self, client: TestClient) -> None:
        """Regular response includes the CORS origin header."""
        resp = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert resp.status_code == 200
        assert (
            resp.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    def test_cors_preflight_allowed(self, client: TestClient) -> None:
        """OPTIONS preflight from any origin is allowed."""
        resp = client.options(
            "/api/games",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert (
            resp.headers.get("access-control-allow-origin")
            == "http://localhost:5173"
        )

    def test_cors_header_on_error(
        self, client: TestClient, mock_fetcher
    ) -> None:
        """CORS headers are present even on error responses."""
        mock_fetcher.fetch_profile_games.side_effect = ValueError(
            "Username must be 1-25 characters"
        )

        resp = client.post(
            "/api/games/fetch-profile",
            json={"username": ""},
            headers={"Origin": "http://localhost:3000"},
        )

        assert resp.status_code == 400
        assert (
            resp.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )
