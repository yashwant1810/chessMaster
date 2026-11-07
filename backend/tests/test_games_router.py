"""Unit tests for the games router (backend/app/routers/games.py).

Tests all four endpoints with mocked dependencies:
- POST /api/games/fetch-profile
- POST /api/games/fetch-url
- GET /api/games
- GET /api/games/{game_id}

Covers success paths and error mapping to correct HTTP status codes.
"""

import sqlite3
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import init_db, insert_game, list_games
from app.models import FetchResult, ParsedGame
from app.routers.games import _get_db, _get_game_fetcher, router
from app.services.chess_api_client import (
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.game_fetcher import GameFetcher
from app.services.pgn_parser import PGNParseError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_db():
    """Create an in-memory SQLite database with the schema initialised.

    ``check_same_thread=False`` is required because FastAPI's TestClient
    runs the ASGI app in a separate thread.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # Reuse the schema constant from the database module
    from app.database import SCHEMA_SQL

    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture()
def mock_fetcher():
    """Return an AsyncMock standing in for GameFetcher."""
    fetcher = AsyncMock(spec=GameFetcher)
    return fetcher


@pytest.fixture()
def client(in_memory_db, mock_fetcher):
    """FastAPI TestClient with overridden dependencies."""
    app = FastAPI()
    app.include_router(router)

    # Override dependency: provide in-memory DB
    app.dependency_overrides[_get_db] = lambda: in_memory_db
    # Override dependency: provide mock fetcher
    app.dependency_overrides[_get_game_fetcher] = lambda: mock_fetcher

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
        moves=["e4", "e5"],
        fens=["fen1", "fen2"],
    )
    defaults.update(overrides)
    return ParsedGame(**defaults)


def _insert_sample_game(conn, game_id="game-1", **overrides):
    """Insert a sample game into the database."""
    game = _sample_game(**overrides)
    insert_game(
        conn,
        game_id=game_id,
        username="testuser",
        pgn_raw='[Event "Live"]\n1. e4 e5 1-0',
        game=game,
    )
    return game_id


# ---------------------------------------------------------------------------
# POST /api/games/fetch-profile
# ---------------------------------------------------------------------------


class TestFetchProfile:
    """Tests for the POST /api/games/fetch-profile endpoint."""

    def test_success(self, client, mock_fetcher):
        """Successful profile fetch returns 200 with game count."""
        mock_fetcher.fetch_profile_games.return_value = FetchResult(
            username="hikaru",
            games_fetched=42,
            is_capped=False,
            message=None,
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "hikaru"
        assert data["games_fetched"] == 42
        assert data["is_capped"] is False

    def test_success_capped(self, client, mock_fetcher):
        """Profile fetch hitting the 10k cap reports is_capped=True."""
        mock_fetcher.fetch_profile_games.return_value = FetchResult(
            username="magnus",
            games_fetched=10_000,
            is_capped=True,
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "magnus"}
        )

        assert resp.status_code == 200
        assert resp.json()["is_capped"] is True
        assert resp.json()["games_fetched"] == 10_000

    def test_no_games_found(self, client, mock_fetcher):
        """Username exists but has no games → 200 with message."""
        mock_fetcher.fetch_profile_games.return_value = FetchResult(
            username="newuser",
            games_fetched=0,
            is_capped=False,
            message="No games found for this username",
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "newuser"}
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["games_fetched"] == 0
        assert "No games found" in data["message"]

    def test_invalid_username_400(self, client, mock_fetcher):
        """Invalid username format → 400."""
        mock_fetcher.fetch_profile_games.side_effect = ValueError(
            "Username must be 1-25 characters"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": ""}
        )

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "invalid_username"

    def test_username_not_found_404(self, client, mock_fetcher):
        """Non-existent chess.com username → 404."""
        mock_fetcher.fetch_profile_games.side_effect = UsernameNotFoundError(
            "nonexistent"
        )

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "nonexistent"}
        )

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "username_not_found"

    def test_timeout_504(self, client, mock_fetcher):
        """chess.com timeout → 504."""
        cause = httpx.ReadTimeout("timed out")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_profile_games.side_effect = exc

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 504
        detail = resp.json()["detail"]
        assert detail["error"] == "upstream_timeout"

    def test_unreachable_502(self, client, mock_fetcher):
        """chess.com unreachable → 502."""
        cause = httpx.ConnectError("connection refused")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_profile_games.side_effect = exc

        resp = client.post(
            "/api/games/fetch-profile", json={"username": "hikaru"}
        )

        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["error"] == "upstream_unreachable"


# ---------------------------------------------------------------------------
# POST /api/games/fetch-url
# ---------------------------------------------------------------------------


class TestFetchURL:
    """Tests for the POST /api/games/fetch-url endpoint."""

    VALID_URL = "https://www.chess.com/game/live/12345"

    def test_success(self, client, mock_fetcher):
        """Successful URL fetch returns 200 with confirmation."""
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
        data = resp.json()
        assert data["games_fetched"] == 1
        assert "Game loaded" in data["message"]

    def test_invalid_url_400(self, client, mock_fetcher):
        """Invalid URL format → 400."""
        mock_fetcher.fetch_game_by_url.side_effect = ValueError(
            "Not a valid chess.com game URL"
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": "https://example.com"}
        )

        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert detail["error"] == "invalid_url"

    def test_game_not_found_404(self, client, mock_fetcher):
        """Non-existent game → 404."""
        mock_fetcher.fetch_game_by_url.side_effect = GameNotFoundError(
            self.VALID_URL
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "game_not_found"

    def test_timeout_504(self, client, mock_fetcher):
        """chess.com timeout during URL fetch → 504."""
        cause = httpx.ReadTimeout("timed out")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_game_by_url.side_effect = exc

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 504
        detail = resp.json()["detail"]
        assert detail["error"] == "upstream_timeout"

    def test_unreachable_502(self, client, mock_fetcher):
        """chess.com unreachable during URL fetch → 502."""
        cause = httpx.ConnectError("connection refused")
        exc = ConnectionFailedError("Connection to chess.com failed")
        exc.__cause__ = cause
        mock_fetcher.fetch_game_by_url.side_effect = exc

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert detail["error"] == "upstream_unreachable"

    def test_pgn_parse_error_422(self, client, mock_fetcher):
        """PGN parse failure after retrieval → 422."""
        mock_fetcher.fetch_game_by_url.side_effect = PGNParseError(
            "Parsing failed at move 3: illegal move"
        )

        resp = client.post(
            "/api/games/fetch-url", json={"url": self.VALID_URL}
        )

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["error"] == "pgn_parse_error"


# ---------------------------------------------------------------------------
# GET /api/games
# ---------------------------------------------------------------------------


class TestListGames:
    """Tests for the GET /api/games endpoint."""

    def test_empty_list(self, client):
        """No fetched games → empty list."""
        resp = client.get("/api/games")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_games(self, client, in_memory_db):
        """Returns all inserted games."""
        _insert_sample_game(in_memory_db, "game-1", date="2024.01.15")
        _insert_sample_game(in_memory_db, "game-2", date="2024.02.20")

        resp = client.get("/api/games")

        assert resp.status_code == 200
        games = resp.json()
        assert len(games) == 2

    def test_default_sort_date_desc(self, client, in_memory_db):
        """Default sort is date descending (most recent first)."""
        _insert_sample_game(in_memory_db, "old", date="2023.01.01")
        _insert_sample_game(in_memory_db, "new", date="2024.06.15")

        resp = client.get("/api/games")

        games = resp.json()
        assert games[0]["id"] == "new"
        assert games[1]["id"] == "old"

    def test_sort_date_asc(self, client, in_memory_db):
        """Sort by date ascending puts oldest first."""
        _insert_sample_game(in_memory_db, "old", date="2023.01.01")
        _insert_sample_game(in_memory_db, "new", date="2024.06.15")

        resp = client.get("/api/games?sort_by=date&order=asc")

        games = resp.json()
        assert games[0]["id"] == "old"
        assert games[1]["id"] == "new"

    def test_sort_by_result(self, client, in_memory_db):
        """Sort by result works without error."""
        _insert_sample_game(in_memory_db, "win-game", result="1-0")
        _insert_sample_game(in_memory_db, "loss-game", result="0-1")

        resp = client.get("/api/games?sort_by=result&order=asc")

        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_sort_by_time_control(self, client, in_memory_db):
        """Sort by time_control works without error."""
        _insert_sample_game(in_memory_db, "g1")
        _insert_sample_game(in_memory_db, "g2")

        resp = client.get("/api/games?sort_by=time_control&order=desc")

        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/games/{game_id}
# ---------------------------------------------------------------------------


class TestGetGame:
    """Tests for the GET /api/games/{game_id} endpoint."""

    def test_found(self, client, in_memory_db):
        """Existing game → 200 with full details."""
        _insert_sample_game(in_memory_db, "game-1")

        resp = client.get("/api/games/game-1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "game-1"
        assert data["white"] == "player1"
        assert data["black"] == "player2"

    def test_not_found_404(self, client):
        """Non-existent game_id → 404."""
        resp = client.get("/api/games/nonexistent")

        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert detail["error"] == "game_not_found"
