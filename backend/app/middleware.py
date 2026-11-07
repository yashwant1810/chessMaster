"""Global exception handling and CORS middleware for the Chess Review Engine.

Maps domain exceptions to structured HTTP error responses per the design
error table, and configures CORS for frontend access.

Requirements: 1.5, 1.6, 1.8, 2.3, 2.4, 2.5, 4.4, 4.5, 5.7, 6.5
"""

import logging

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.chess_api_client import (
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.pgn_parser import PGNParseError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Additional domain exceptions handled by the middleware
# ---------------------------------------------------------------------------


class AnalysisNotFoundError(Exception):
    """Raised when analysis results are requested but do not exist."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.message = "Analysis not available. Run analysis first."
        super().__init__(self.message)


class AnalysisInProgressError(Exception):
    """Raised when analysis is requested for a game already being analysed."""

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self.message = "Analysis is already running for this game"
        super().__init__(self.message)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers mapping domain errors to HTTP responses.

    Error mapping (from design document):
        ValueError (invalid username/URL) → 400
        UsernameNotFoundError             → 404
        GameNotFoundError                 → 404
        AnalysisNotFoundError             → 404
        AnalysisInProgressError           → 409
        PGNParseError                     → 422
        ConnectionFailedError (timeout)   → 504
        ConnectionFailedError (network)   → 502
    """

    @app.exception_handler(ValueError)
    async def value_error_handler(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Handle validation errors (invalid username or URL) → 400."""
        message = str(exc)
        # Determine error code from the message content.  The validators
        # produce well-defined messages containing "URL" for URL errors.
        error_code = (
            "invalid_url" if "url" in message.lower() else "invalid_username"
        )
        return JSONResponse(
            status_code=400,
            content={"error": error_code, "message": message},
        )

    @app.exception_handler(UsernameNotFoundError)
    async def username_not_found_handler(
        request: Request, exc: UsernameNotFoundError
    ) -> JSONResponse:
        """Handle username not found on chess.com → 404."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "username_not_found",
                "message": exc.message,
            },
        )

    @app.exception_handler(GameNotFoundError)
    async def game_not_found_handler(
        request: Request, exc: GameNotFoundError
    ) -> JSONResponse:
        """Handle game not found on chess.com → 404."""
        return JSONResponse(
            status_code=404,
            content={"error": "game_not_found", "message": exc.message},
        )

    @app.exception_handler(AnalysisNotFoundError)
    async def analysis_not_found_handler(
        request: Request, exc: AnalysisNotFoundError
    ) -> JSONResponse:
        """Handle analysis not yet available → 404."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "analysis_not_found",
                "message": exc.message,
            },
        )

    @app.exception_handler(AnalysisInProgressError)
    async def analysis_in_progress_handler(
        request: Request, exc: AnalysisInProgressError
    ) -> JSONResponse:
        """Handle analysis already running → 409."""
        return JSONResponse(
            status_code=409,
            content={
                "error": "analysis_in_progress",
                "message": exc.message,
            },
        )

    @app.exception_handler(PGNParseError)
    async def pgn_parse_error_handler(
        request: Request, exc: PGNParseError
    ) -> JSONResponse:
        """Handle PGN parsing failures → 422."""
        return JSONResponse(
            status_code=422,
            content={"error": "pgn_parse_error", "message": exc.message},
        )

    @app.exception_handler(ConnectionFailedError)
    async def connection_failed_handler(
        request: Request, exc: ConnectionFailedError
    ) -> JSONResponse:
        """Handle chess.com connection failures → 502 (network) or 504 (timeout)."""
        # Distinguish timeout from network errors by inspecting the
        # chained cause set by the API client via ``raise … from exc``.
        if isinstance(exc.__cause__, httpx.TimeoutException):
            return JSONResponse(
                status_code=504,
                content={
                    "error": "upstream_timeout",
                    "message": exc.message,
                },
            )
        return JSONResponse(
            status_code=502,
            content={
                "error": "upstream_unreachable",
                "message": exc.message,
            },
        )


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware allowing the frontend origin.

    In the Docker Compose development setup the frontend runs on a
    different port, so all origins are permitted.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
