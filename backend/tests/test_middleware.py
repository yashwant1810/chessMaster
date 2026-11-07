"""Tests for global exception handling and CORS middleware.

Verifies that domain exceptions are mapped to correct HTTP status codes
and structured error responses per the design error table.
"""

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.middleware import (
    AnalysisInProgressError,
    AnalysisNotFoundError,
    setup_cors,
    setup_exception_handlers,
)
from app.services.chess_api_client import (
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.pgn_parser import PGNParseError


@pytest.fixture()
def app() -> FastAPI:
    """Create a test FastAPI app with middleware configured."""
    test_app = FastAPI()
    setup_cors(test_app)
    setup_exception_handlers(test_app)

    # Endpoints that raise each domain exception for testing.

    @test_app.get("/raise-value-error-username")
    async def _raise_value_error_username():
        raise ValueError("Username must be 1-25 characters")

    @test_app.get("/raise-value-error-url")
    async def _raise_value_error_url():
        raise ValueError("Not a valid chess.com game URL")

    @test_app.get("/raise-username-not-found")
    async def _raise_username_not_found():
        raise UsernameNotFoundError("testplayer")

    @test_app.get("/raise-game-not-found")
    async def _raise_game_not_found():
        raise GameNotFoundError("https://www.chess.com/game/live/99999")

    @test_app.get("/raise-connection-timeout")
    async def _raise_connection_timeout():
        try:
            raise httpx.ReadTimeout("timed out")
        except httpx.TimeoutException as cause:
            raise ConnectionFailedError("Connection to chess.com failed") from cause

    @test_app.get("/raise-connection-network")
    async def _raise_connection_network():
        try:
            raise httpx.ConnectError("connection refused")
        except httpx.ConnectError as cause:
            raise ConnectionFailedError("Connection to chess.com failed") from cause

    @test_app.get("/raise-pgn-parse-error")
    async def _raise_pgn_parse_error():
        raise PGNParseError("Invalid move at move 5: illegal san", location="move 5")

    @test_app.get("/raise-analysis-not-found")
    async def _raise_analysis_not_found():
        raise AnalysisNotFoundError("game-123")

    @test_app.get("/raise-analysis-in-progress")
    async def _raise_analysis_in_progress():
        raise AnalysisInProgressError("game-123")

    return test_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Create a test client for the app."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# ValueError → 400
# ---------------------------------------------------------------------------


class TestValueErrorHandler:
    """ValueError maps to 400 with the correct error code."""

    def test_invalid_username_returns_400(self, client: TestClient) -> None:
        resp = client.get("/raise-value-error-username")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "invalid_username"
        assert "1-25 characters" in body["message"]

    def test_invalid_url_returns_400(self, client: TestClient) -> None:
        resp = client.get("/raise-value-error-url")
        assert resp.status_code == 400
        body = resp.json()
        assert body["error"] == "invalid_url"
        assert "chess.com game URL" in body["message"]


# ---------------------------------------------------------------------------
# UsernameNotFoundError → 404
# ---------------------------------------------------------------------------


class TestUsernameNotFoundHandler:
    def test_returns_404(self, client: TestClient) -> None:
        resp = client.get("/raise-username-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "username_not_found"
        assert "testplayer" in body["message"]


# ---------------------------------------------------------------------------
# GameNotFoundError → 404
# ---------------------------------------------------------------------------


class TestGameNotFoundHandler:
    def test_returns_404(self, client: TestClient) -> None:
        resp = client.get("/raise-game-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "game_not_found"
        assert "99999" in body["message"]


# ---------------------------------------------------------------------------
# ConnectionFailedError → 502 / 504
# ---------------------------------------------------------------------------


class TestConnectionFailedHandler:
    def test_timeout_returns_504(self, client: TestClient) -> None:
        resp = client.get("/raise-connection-timeout")
        assert resp.status_code == 504
        body = resp.json()
        assert body["error"] == "upstream_timeout"
        assert "chess.com" in body["message"]

    def test_network_error_returns_502(self, client: TestClient) -> None:
        resp = client.get("/raise-connection-network")
        assert resp.status_code == 502
        body = resp.json()
        assert body["error"] == "upstream_unreachable"
        assert "chess.com" in body["message"]


# ---------------------------------------------------------------------------
# PGNParseError → 422
# ---------------------------------------------------------------------------


class TestPGNParseErrorHandler:
    def test_returns_422(self, client: TestClient) -> None:
        resp = client.get("/raise-pgn-parse-error")
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"] == "pgn_parse_error"
        assert "move 5" in body["message"]


# ---------------------------------------------------------------------------
# AnalysisNotFoundError → 404
# ---------------------------------------------------------------------------


class TestAnalysisNotFoundHandler:
    def test_returns_404(self, client: TestClient) -> None:
        resp = client.get("/raise-analysis-not-found")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"] == "analysis_not_found"
        assert "Run analysis first" in body["message"]


# ---------------------------------------------------------------------------
# AnalysisInProgressError → 409
# ---------------------------------------------------------------------------


class TestAnalysisInProgressHandler:
    def test_returns_409(self, client: TestClient) -> None:
        resp = client.get("/raise-analysis-in-progress")
        assert resp.status_code == 409
        body = resp.json()
        assert body["error"] == "analysis_in_progress"
        assert "already running" in body["message"]


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    def test_cors_allows_any_origin(self, client: TestClient) -> None:
        """Preflight request from any origin should be allowed."""
        resp = client.options(
            "/raise-value-error-username",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_headers_on_response(self, client: TestClient) -> None:
        """Regular requests include the CORS origin header."""
        resp = client.get(
            "/raise-value-error-username",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Error response shape
# ---------------------------------------------------------------------------


class TestErrorResponseShape:
    """Every error response includes exactly 'error' and 'message' keys."""

    @pytest.mark.parametrize(
        "path",
        [
            "/raise-value-error-username",
            "/raise-value-error-url",
            "/raise-username-not-found",
            "/raise-game-not-found",
            "/raise-connection-timeout",
            "/raise-connection-network",
            "/raise-pgn-parse-error",
            "/raise-analysis-not-found",
            "/raise-analysis-in-progress",
        ],
    )
    def test_response_has_error_and_message(
        self, client: TestClient, path: str
    ) -> None:
        resp = client.get(path)
        body = resp.json()
        assert "error" in body, f"Missing 'error' key in response from {path}"
        assert "message" in body, f"Missing 'message' key in response from {path}"
        assert isinstance(body["error"], str)
        assert isinstance(body["message"], str)
