"""SQLite database access layer for the Chess Review Engine.

Provides schema initialization, connection management, and CRUD operations
for games, analysis results, and analysis summaries. Write operations are
wrapped in transactions with a single retry on failure.
"""

import json
from datetime import datetime, timezone
import sqlite3
import uuid
from functools import wraps
from pathlib import Path
from typing import Any

from app.models import ParsedGame, PlayerAnalysisSummary

DEFAULT_DB_PATH = Path(__file__).parent.parent / "chess_review.db"

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS games (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    pgn_raw TEXT NOT NULL,
    event TEXT,
    site TEXT,
    date_played TEXT,
    round TEXT,
    white TEXT NOT NULL,
    black TEXT NOT NULL,
    result TEXT NOT NULL,
    time_control TEXT,
    opening_name TEXT,
    additional_headers TEXT,
    moves TEXT NOT NULL,
    comments TEXT,
    fens TEXT NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL REFERENCES games(id),
    move_index INTEGER NOT NULL,
    is_white BOOLEAN NOT NULL,
    move_san TEXT NOT NULL,
    fen_before TEXT NOT NULL,
    fen_after TEXT NOT NULL,
    eval_before INTEGER,
    mate_before INTEGER,
    eval_after INTEGER,
    mate_after INTEGER,
    classification TEXT,
    centipawn_loss INTEGER,
    candidate_moves TEXT,
    insight TEXT,
    UNIQUE(game_id, move_index)
);

CREATE TABLE IF NOT EXISTS analysis_summaries (
    game_id TEXT PRIMARY KEY REFERENCES games(id),
    is_complete BOOLEAN NOT NULL DEFAULT FALSE,
    white_best INTEGER DEFAULT 0,
    white_excellent INTEGER DEFAULT 0,
    white_good INTEGER DEFAULT 0,
    white_inaccuracy INTEGER DEFAULT 0,
    white_mistake INTEGER DEFAULT 0,
    white_blunder INTEGER DEFAULT 0,
    white_performance_ratings TEXT,
    white_final_rating INTEGER,
    black_best INTEGER DEFAULT 0,
    black_excellent INTEGER DEFAULT 0,
    black_good INTEGER DEFAULT 0,
    black_inaccuracy INTEGER DEFAULT 0,
    black_mistake INTEGER DEFAULT 0,
    black_blunder INTEGER DEFAULT 0,
    black_performance_ratings TEXT,
    black_final_rating INTEGER
);

CREATE INDEX IF NOT EXISTS idx_games_username ON games(username);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date_played);
CREATE INDEX IF NOT EXISTS idx_analysis_game ON analysis_results(game_id);
"""


# ---------------------------------------------------------------------------
# Connection and schema helpers
# ---------------------------------------------------------------------------


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Initialize the database schema. Safe to call multiple times."""
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Retry decorator for write operations
# ---------------------------------------------------------------------------


def _with_retry(func):
    """Retry a write operation once on ``sqlite3.Error``."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error:
            # Single retry – transient lock / busy errors
            return func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Game CRUD
# ---------------------------------------------------------------------------


@_with_retry
def insert_game(
    conn: sqlite3.Connection,
    game_id: str,
    username: str,
    pgn_raw: str,
    game: ParsedGame,
    time_control: str | None = None,
    opening_name: str | None = None,
    end_time: int | None = None,
) -> str:
    """Insert a parsed game into the database.

    ``time_control`` and ``opening_name`` fall back to values extracted
    from *game.additional_headers* when not provided explicitly.

    Returns the *game_id*.
    """
    if time_control is None:
        time_control = game.additional_headers.get("TimeControl")
    if opening_name is None:
        opening_name = (
            game.additional_headers.get("Opening")
            or game.additional_headers.get("ECOUrl")
        )

    with conn:
        conn.execute(
            """
            INSERT INTO games (
                id, username, pgn_raw, event, site, date_played, round,
                white, black, result, time_control, opening_name,
                additional_headers, moves, comments, fens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id,
                username,
                pgn_raw,
                game.event,
                game.site,
                (
                    datetime.fromtimestamp(end_time, tz=timezone.utc).isoformat()
                    if end_time
                    else game.date
                ),
                game.round,
                game.white,
                game.black,
                game.result,
                time_control,
                opening_name,
                json.dumps(game.additional_headers),
                json.dumps(game.moves),
                json.dumps(game.comments),
                json.dumps(game.fens),
            ),
        )
    return game_id


def get_game(conn: sqlite3.Connection, game_id: str) -> dict[str, Any] | None:
    """Retrieve a game by ID.

    Returns a dict with all game columns (JSON fields deserialized),
    or ``None`` if the game does not exist.
    """
    row = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    if row is None:
        return None
    return _row_to_game_dict(row)


def list_games(
    conn: sqlite3.Connection,
    username: str | None = None,
    sort_by: str = "date_played",
    order: str = "DESC",
) -> list[dict[str, Any]]:
    """List games, optionally filtered by *username* and sorted.

    *sort_by* must be one of ``date_played``, ``result``, or
    ``time_control``; defaults to ``date_played``.
    *order* must be ``ASC`` or ``DESC``; defaults to ``DESC``.
    """
    allowed_sort_columns = {"date_played", "result", "time_control"}
    if sort_by not in allowed_sort_columns:
        sort_by = "date_played"
    if order.upper() not in ("ASC", "DESC"):
        order = "DESC"

    query = "SELECT * FROM games"
    params: list[Any] = []

    if username is not None:
        query += " WHERE username = ?"
        params.append(username)

    # sort_by is validated above – safe to interpolate
    query += f" ORDER BY {sort_by} {order.upper()}"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_game_dict(row) for row in rows]


def _row_to_game_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a *games* table row to a dict with deserialized JSON."""
    d = dict(row)
    d["additional_headers"] = (
        json.loads(d["additional_headers"]) if d["additional_headers"] else {}
    )
    d["moves"] = json.loads(d["moves"]) if d["moves"] else []
    d["comments"] = json.loads(d["comments"]) if d["comments"] else []
    d["fens"] = json.loads(d["fens"]) if d["fens"] else []
    return d


# ---------------------------------------------------------------------------
# Analysis Result CRUD
# ---------------------------------------------------------------------------


@_with_retry
def insert_analysis_result(
    conn: sqlite3.Connection,
    game_id: str,
    move_index: int,
    is_white: bool,
    move_san: str,
    fen_before: str,
    fen_after: str,
    eval_before: int | None = None,
    mate_before: int | None = None,
    eval_after: int | None = None,
    mate_after: int | None = None,
    classification: str | None = None,
    centipawn_loss: int | None = None,
    candidate_moves: list[dict] | None = None,
    insight: dict | None = None,
) -> str:
    """Insert a single move analysis result.

    Uses ``INSERT OR REPLACE`` so re-analysis overwrites previous results
    for the same *(game_id, move_index)*.

    Returns the generated result ID.
    """
    result_id = str(uuid.uuid4())
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO analysis_results (
                id, game_id, move_index, is_white, move_san,
                fen_before, fen_after,
                eval_before, mate_before, eval_after, mate_after,
                classification, centipawn_loss,
                candidate_moves, insight
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                game_id,
                move_index,
                is_white,
                move_san,
                fen_before,
                fen_after,
                eval_before,
                mate_before,
                eval_after,
                mate_after,
                classification,
                centipawn_loss,
                json.dumps(candidate_moves) if candidate_moves is not None else None,
                json.dumps(insight) if insight is not None else None,
            ),
        )
    return result_id


def get_analysis(
    conn: sqlite3.Connection, game_id: str
) -> list[dict[str, Any]]:
    """Retrieve all analysis results for a game, ordered by move_index.

    Returns a list of dicts with deserialized JSON fields.
    Returns an empty list when no results exist.
    """
    rows = conn.execute(
        "SELECT * FROM analysis_results WHERE game_id = ? ORDER BY move_index",
        (game_id,),
    ).fetchall()
    return [_row_to_analysis_dict(row) for row in rows]


def _row_to_analysis_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert an *analysis_results* row to a dict with deserialized JSON."""
    d = dict(row)
    d["candidate_moves"] = (
        json.loads(d["candidate_moves"]) if d["candidate_moves"] else []
    )
    d["insight"] = json.loads(d["insight"]) if d["insight"] else None
    d["is_white"] = bool(d["is_white"])
    return d


# ---------------------------------------------------------------------------
# Analysis Summary CRUD
# ---------------------------------------------------------------------------


@_with_retry
def upsert_analysis_summary(
    conn: sqlite3.Connection,
    game_id: str,
    is_complete: bool,
    white_summary: PlayerAnalysisSummary,
    black_summary: PlayerAnalysisSummary,
) -> None:
    """Insert or update the analysis summary for a game.

    Uses ``ON CONFLICT … DO UPDATE`` so the summary can be written
    incrementally during analysis and finalized when complete.
    """
    with conn:
        conn.execute(
            """
            INSERT INTO analysis_summaries (
                game_id, is_complete,
                white_best, white_excellent, white_good,
                white_inaccuracy, white_mistake, white_blunder,
                white_performance_ratings, white_final_rating,
                black_best, black_excellent, black_good,
                black_inaccuracy, black_mistake, black_blunder,
                black_performance_ratings, black_final_rating
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(game_id) DO UPDATE SET
                is_complete = excluded.is_complete,
                white_best = excluded.white_best,
                white_excellent = excluded.white_excellent,
                white_good = excluded.white_good,
                white_inaccuracy = excluded.white_inaccuracy,
                white_mistake = excluded.white_mistake,
                white_blunder = excluded.white_blunder,
                white_performance_ratings = excluded.white_performance_ratings,
                white_final_rating = excluded.white_final_rating,
                black_best = excluded.black_best,
                black_excellent = excluded.black_excellent,
                black_good = excluded.black_good,
                black_inaccuracy = excluded.black_inaccuracy,
                black_mistake = excluded.black_mistake,
                black_blunder = excluded.black_blunder,
                black_performance_ratings = excluded.black_performance_ratings,
                black_final_rating = excluded.black_final_rating
            """,
            (
                game_id,
                is_complete,
                white_summary.best_count,
                white_summary.excellent_count,
                white_summary.good_count,
                white_summary.inaccuracy_count,
                white_summary.mistake_count,
                white_summary.blunder_count,
                json.dumps(white_summary.performance_ratings),
                white_summary.final_performance_rating,
                black_summary.best_count,
                black_summary.excellent_count,
                black_summary.good_count,
                black_summary.inaccuracy_count,
                black_summary.mistake_count,
                black_summary.blunder_count,
                json.dumps(black_summary.performance_ratings),
                black_summary.final_performance_rating,
            ),
        )


def get_analysis_summary(
    conn: sqlite3.Connection, game_id: str
) -> dict[str, Any] | None:
    """Retrieve the analysis summary for a game.

    Returns a dict with deserialized JSON fields, or ``None`` if no
    summary exists.
    """
    row = conn.execute(
        "SELECT * FROM analysis_summaries WHERE game_id = ?", (game_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_summary_dict(row)


def _row_to_summary_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert an *analysis_summaries* row to a dict with deserialized JSON."""
    d = dict(row)
    d["is_complete"] = bool(d["is_complete"])
    d["white_performance_ratings"] = (
        json.loads(d["white_performance_ratings"])
        if d["white_performance_ratings"]
        else []
    )
    d["black_performance_ratings"] = (
        json.loads(d["black_performance_ratings"])
        if d["black_performance_ratings"]
        else []
    )
    return d
