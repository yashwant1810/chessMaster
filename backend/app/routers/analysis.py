"""Analysis API endpoints.

Provides endpoints to start Stockfish analysis on a game, poll progress,
and retrieve completed analysis results.

Requirements: 5.1, 5.5, 5.6
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.database import (
    get_analysis,
    get_analysis_summary,
    get_connection,
    get_game,
)
from app.models import AnalysisStatus
from app.services.review_engine import ReviewEngine
from app.services.stockfish_engine import StockfishEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# ---------------------------------------------------------------------------
# In-memory tracking for running analyses
# ---------------------------------------------------------------------------
# Maps game_id → AnalysisStatus for analyses that are currently in progress.
# Entries are added when POST starts an analysis and removed when the
# background task finishes (either successfully or on error).  The status
# endpoint reads from this dict for live progress and falls back to the
# database for completed analyses.

_running_analyses: dict[str, AnalysisStatus] = {}


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_db():
    """Yield a database connection, closing it when the request ends."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


def _run_analysis_task(game_id: str) -> None:
    """Execute game analysis as a background task.

    Creates its own DB connection and StockfishEngine for thread safety,
    since FastAPI BackgroundTasks run in a thread pool separate from the
    request-handling thread.
    """
    conn = get_connection()
    engine = StockfishEngine()
    try:
        review_engine = ReviewEngine(engine, conn)

        def progress_callback(
            positions_analyzed: int, total_positions: int
        ) -> None:
            _running_analyses[game_id] = AnalysisStatus(
                game_id=game_id,
                total_positions=total_positions,
                positions_analyzed=positions_analyzed,
                is_complete=positions_analyzed >= total_positions,
            )

        review_engine.analyze_game(
            game_id, progress_callback=progress_callback
        )
    except Exception:
        logger.exception("Analysis failed for game %s", game_id)
    finally:
        engine.stop()
        conn.close()
        # Remove from in-flight set — the DB now has the results.
        _running_analyses.pop(game_id, None)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{game_id}")
async def start_analysis(
    game_id: str,
    background_tasks: BackgroundTasks,
    conn=Depends(_get_db),
) -> JSONResponse:
    """Start Stockfish analysis for a game.

    Returns 202 on success (analysis started).
    Returns 200 if analysis is already complete.
    Returns 409 if analysis is currently running.
    Returns 404 if the game does not exist.
    """
    # Verify the game exists in the database.
    game = get_game(conn, game_id)
    if game is None:
        return JSONResponse(
            status_code=404,
            content={"error": "game_not_found", "message": "Game not found"},
        )

    # Check if analysis is already complete in the database.
    summary = get_analysis_summary(conn, game_id)
    if summary is not None and summary["is_complete"]:
        return JSONResponse(
            status_code=200,
            content={
                "game_id": game_id,
                "message": "Analysis already complete",
                "is_complete": True,
            },
        )

    # Check if analysis is currently running (in-memory tracking).
    if game_id in _running_analyses:
        return JSONResponse(
            status_code=409,
            content={
                "error": "analysis_in_progress",
                "message": "Analysis is already running for this game",
            },
        )

    # Seed progress tracking before launching the background task.
    total_moves = len(game["moves"])
    _running_analyses[game_id] = AnalysisStatus(
        game_id=game_id,
        total_positions=total_moves,
        positions_analyzed=0,
        is_complete=False,
    )

    # Schedule analysis in the background.
    background_tasks.add_task(_run_analysis_task, game_id)

    return JSONResponse(
        status_code=202,
        content={
            "game_id": game_id,
            "message": "Analysis started",
            "total_positions": total_moves,
        },
    )


@router.get("/{game_id}")
async def get_analysis_results(
    game_id: str,
    conn=Depends(_get_db),
) -> dict[str, Any]:
    """Return complete analysis results for a game.

    Returns 404 if the game has not been analyzed yet.
    """
    analysis_moves = get_analysis(conn, game_id)
    summary = get_analysis_summary(conn, game_id)

    if not analysis_moves or summary is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "analysis_not_found",
                "message": "Analysis not available. Run analysis first.",
            },
        )

    # Transform flat DB rows to nested objects matching frontend types
    transformed_moves = []
    for m in analysis_moves:
        transformed_moves.append({
            "move_number": m.get("move_index", 0) // 2 + 1,
            "is_white": bool(m.get("is_white")),
            "move_san": m.get("move_san", ""),
            "position_before": m.get("fen_before", ""),
            "position_after": m.get("fen_after", ""),
            "evaluation_before": {
                "fen": m.get("fen_before", ""),
                "evaluation": m.get("eval_before"),
                "mate_in": m.get("mate_before"),
                "candidate_moves": [],
                "is_error": False,
            },
            "evaluation_after": {
                "fen": m.get("fen_after", ""),
                "evaluation": m.get("eval_after"),
                "mate_in": m.get("mate_after"),
                "candidate_moves": m.get("candidate_moves", []),
                "is_error": False,
            },
            "classification": m.get("classification"),
            "centipawn_loss": m.get("centipawn_loss"),
            "candidate_moves": m.get("candidate_moves", []),
            "insight": m.get("insight"),
        })

    return {
        "game_id": game_id,
        "moves": transformed_moves,
        "white_summary": {
            "best_count": summary["white_best"],
            "excellent_count": summary["white_excellent"],
            "good_count": summary["white_good"],
            "inaccuracy_count": summary["white_inaccuracy"],
            "mistake_count": summary["white_mistake"],
            "blunder_count": summary["white_blunder"],
            "performance_ratings": summary["white_performance_ratings"] or [],
            "final_performance_rating": summary["white_final_rating"] or 0,
        },
        "black_summary": {
            "best_count": summary["black_best"],
            "excellent_count": summary["black_excellent"],
            "good_count": summary["black_good"],
            "inaccuracy_count": summary["black_inaccuracy"],
            "mistake_count": summary["black_mistake"],
            "blunder_count": summary["black_blunder"],
            "performance_ratings": summary["black_performance_ratings"] or [],
            "final_performance_rating": summary["black_final_rating"] or 0,
        },
        "evaluations": [m.get("eval_after") for m in analysis_moves],
        "is_complete": summary["is_complete"],
    }


@router.get("/{game_id}/status")
async def get_analysis_status(
    game_id: str,
    conn=Depends(_get_db),
) -> dict[str, Any]:
    """Return analysis progress for a game.

    Checks in-memory tracking for active analyses first, then falls
    back to the database for completed analyses.  Returns 404 if
    no analysis has been started for the game.
    """
    # Check in-memory tracking first (active analysis).
    if game_id in _running_analyses:
        status = _running_analyses[game_id]
        return {
            "game_id": status.game_id,
            "total_positions": status.total_positions,
            "positions_analyzed": status.positions_analyzed,
            "percentage": status.percentage,
            "is_complete": status.is_complete,
        }

    # Fall back to the database for completed analyses.
    summary = get_analysis_summary(conn, game_id)
    if summary is not None:
        analysis_moves = get_analysis(conn, game_id)
        total = len(analysis_moves)
        return {
            "game_id": game_id,
            "total_positions": total,
            "positions_analyzed": total,
            "percentage": 100 if summary["is_complete"] else 0,
            "is_complete": summary["is_complete"],
        }

    # No analysis found at all.
    return JSONResponse(
        status_code=404,
        content={
            "error": "analysis_not_found",
            "message": "Analysis not available. Run analysis first.",
        },
    )
