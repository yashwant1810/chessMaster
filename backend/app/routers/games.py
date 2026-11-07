"""Game fetching and listing API endpoints.

Provides endpoints for fetching games from chess.com by profile or URL,
listing fetched games with sorting, and retrieving individual game details.

Requirements: 1.1, 1.3, 1.4, 1.6, 1.7, 1.8, 2.1, 2.3, 2.4, 2.6, 2.7,
              3.1, 3.4, 3.5
"""

import sqlite3
from enum import Enum
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_connection, get_game, list_games
from app.services.chess_api_client import (
    ChessComAPIClient,
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.game_fetcher import GameFetcher
from app.services.pgn_parser import PGNParseError

router = APIRouter(prefix="/api/games", tags=["games"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class FetchProfileRequest(BaseModel):
    """Request body for fetching games by chess.com username."""

    username: str = Field(
        ..., description="Chess.com username to fetch games for"
    )


class FetchURLRequest(BaseModel):
    """Request body for fetching a single game by chess.com URL."""

    url: str = Field(..., description="Chess.com game URL")


class FetchResponse(BaseModel):
    """Response for game fetch operations."""

    username: str
    games_fetched: int
    is_capped: bool = False
    message: str | None = None


class SortField(str, Enum):
    """Allowed sort fields for the game list."""

    date = "date"
    result = "result"
    time_control = "time_control"


class SortOrder(str, Enum):
    """Allowed sort orders for the game list."""

    asc = "asc"
    desc = "desc"


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

# Mapping from API sort field names to database column names.
_SORT_FIELD_TO_COLUMN: dict[str, str] = {
    "date": "date_played",
    "result": "result",
    "time_control": "time_control",
}


def _get_db():
    """Provide a SQLite connection for the request lifetime."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


async def _get_game_fetcher(
    conn: sqlite3.Connection = Depends(_get_db),
):
    """Provide a GameFetcher instance backed by a fresh API client."""
    api_client = ChessComAPIClient()
    try:
        yield GameFetcher(api_client=api_client, db_conn=conn)
    finally:
        await api_client.close()


# Type aliases for Depends injection
DBConn = Annotated[sqlite3.Connection, Depends(_get_db)]
Fetcher = Annotated[GameFetcher, Depends(_get_game_fetcher)]


# ---------------------------------------------------------------------------
# Error-mapping helper
# ---------------------------------------------------------------------------


def _connection_error_status(exc: ConnectionFailedError) -> int:
    """Return 504 for timeouts, 502 for all other connection errors."""
    cause = exc.__cause__
    if isinstance(cause, httpx.TimeoutException):
        return 504
    return 502


def _connection_error_body(exc: ConnectionFailedError) -> dict[str, str]:
    """Return the JSON error body for a connection failure."""
    cause = exc.__cause__
    if isinstance(cause, httpx.TimeoutException):
        return {
            "error": "upstream_timeout",
            "message": "Connection to chess.com failed",
        }
    return {
        "error": "upstream_unreachable",
        "message": "Connection to chess.com failed",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/fetch-profile", response_model=FetchResponse)
async def fetch_profile(body: FetchProfileRequest, fetcher: Fetcher) -> Any:
    """Fetch all games for a chess.com username.

    Validates the username, retrieves up to 10,000 most recent games
    from the chess.com public API, parses each PGN, and stores results
    locally.

    Returns the count of games fetched and whether the cap was reached.
    On success with zero games, returns ``games_fetched=0`` with a
    descriptive message (Requirement 1.7).
    """
    try:
        result = await fetcher.fetch_profile_games(body.username)
    except ValueError as exc:
        # Invalid username format (Requirement 1.6)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_username", "message": str(exc)},
        ) from exc
    except UsernameNotFoundError as exc:
        # Username does not exist on chess.com (Requirement 1.8)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "username_not_found",
                "message": exc.message,
            },
        ) from exc
    except ConnectionFailedError as exc:
        # Timeout or unreachable (Requirements 1.5)
        raise HTTPException(
            status_code=_connection_error_status(exc),
            detail=_connection_error_body(exc),
        ) from exc

    return FetchResponse(
        username=result.username,
        games_fetched=result.games_fetched,
        is_capped=result.is_capped,
        message=result.message,
    )


@router.post("/fetch-url", response_model=FetchResponse)
async def fetch_url(body: FetchURLRequest, fetcher: Fetcher) -> Any:
    """Fetch a single game by its chess.com game URL.

    Validates the URL format, retrieves the game, parses the PGN,
    and stores the result locally.  Returns a confirmation message
    on success (Requirement 2.6) or an appropriate error.
    """
    try:
        result = await fetcher.fetch_game_by_url(body.url)
    except ValueError as exc:
        # Invalid URL format (Requirement 2.3)
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_url", "message": str(exc)},
        ) from exc
    except GameNotFoundError as exc:
        # Game does not exist on chess.com (Requirement 2.4)
        raise HTTPException(
            status_code=404,
            detail={"error": "game_not_found", "message": exc.message},
        ) from exc
    except ConnectionFailedError as exc:
        # Timeout or unreachable (Requirement 2.5)
        raise HTTPException(
            status_code=_connection_error_status(exc),
            detail=_connection_error_body(exc),
        ) from exc
    except PGNParseError as exc:
        # PGN parsing failure after successful retrieval (Requirement 2.7)
        raise HTTPException(
            status_code=422,
            detail={"error": "pgn_parse_error", "message": exc.message},
        ) from exc

    return FetchResponse(
        username=result.username,
        games_fetched=result.games_fetched,
        is_capped=result.is_capped,
        message=result.message,
    )


@router.get("")
async def list_fetched_games(
    conn: DBConn,
    sort_by: SortField = Query(SortField.date, description="Field to sort by"),
    order: SortOrder = Query(SortOrder.desc, description="Sort order"),
) -> list[dict[str, Any]]:
    """List fetched games with optional sorting.

    Returns lightweight GameSummary objects (not full game data with PGN).
    Supports sorting by ``date`` (default), ``result``, or
    ``time_control`` in ascending or descending order.  Defaults to
    date descending (most recent first) per Requirement 3.1.

    Returns an empty list when no games have been fetched
    (Requirement 3.5).
    """
    db_sort_column = _SORT_FIELD_TO_COLUMN.get(sort_by.value, "date_played")
    db_order = order.value.upper()

    # Lightweight query: only summary fields, no PGN/moves/fens
    allowed = {"date_played", "result", "time_control"}
    col = db_sort_column if db_sort_column in allowed else "date_played"
    direction = db_order if db_order in ("ASC", "DESC") else "DESC"

    query = f"""
        SELECT g.id, g.username, g.date_played, g.white, g.black,
               g.result, g.time_control, g.opening_name,
               CASE WHEN s.game_id IS NOT NULL AND s.is_complete = 1
                    THEN 1 ELSE 0 END AS is_analyzed
        FROM games g
        LEFT JOIN analysis_summaries s ON g.id = s.game_id
        ORDER BY g.{col} {direction}
    """
    rows = conn.execute(query).fetchall()

    summaries = []
    for row in rows:
        r = dict(row)
        # Determine opponent from username vs white/black
        username = r["username"]
        if r["white"] and r["white"].lower() == username.lower():
            opponent = r["black"] or "Unknown"
            # Translate result from PGN perspective to player perspective
            pgn_result = r["result"]
            if pgn_result == "1-0":
                player_result = "win"
            elif pgn_result == "0-1":
                player_result = "loss"
            else:
                player_result = "draw"
        else:
            opponent = r["white"] or "Unknown"
            pgn_result = r["result"]
            if pgn_result == "0-1":
                player_result = "win"
            elif pgn_result == "1-0":
                player_result = "loss"
            else:
                player_result = "draw"

        summaries.append({
            "game_id": r["id"],
            "date_played": r["date_played"] or "",
            "opponent": opponent,
            "result": player_result,
            "time_control": r["time_control"],
            "opening_name": r["opening_name"],
            "is_analyzed": bool(r["is_analyzed"]),
        })

    return summaries


@router.get("/{game_id}")
async def get_game_details(game_id: str, conn: DBConn) -> dict[str, Any]:
    """Return details for a single fetched game.

    Raises 404 when the game ID does not exist in the local database.
    """
    game = get_game(conn, game_id)
    if game is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "game_not_found", "message": "Game not found"},
        )
    return game
