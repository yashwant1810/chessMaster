"""Full game analysis orchestration using Stockfish.

Loads a game from the database, evaluates every position with Stockfish,
classifies moves, computes performance ratings, generates learning insights,
stores results, and returns the complete analysis.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.4, 8.1, 9.1
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable

import chess

from app.database import (
    get_game,
    insert_analysis_result,
    upsert_analysis_summary,
)
from app.models import (
    AnalyzedMove,
    GameAnalysis,
    MoveClassification,
    PlayerAnalysisSummary,
    PositionEvaluation,
)
from app.services.insight_generator import generate_insight
from app.services.move_classifier import (
    classify_move_safe,
    compute_classification_summary,
)
from app.services.performance_rating import (
    compute_cumulative_ratings,
    compute_performance_rating,
)
from app.services.stockfish_engine import StockfishEngine

logger = logging.getLogger(__name__)

# Classifications that trigger learning insight generation.
_INSIGHT_CLASSIFICATIONS = frozenset(
    {
        MoveClassification.INACCURACY,
        MoveClassification.MISTAKE,
        MoveClassification.BLUNDER,
    }
)

# Large centipawn equivalent used when converting mate-in-N to centipawns.
_MATE_CP_BASE = 10_000
_MATE_CP_STEP = 10

# Type alias for progress callbacks: (positions_analyzed, total_positions).
ProgressCallback = Callable[[int, int], None]


def _eval_to_cp(evaluation: int | None, mate_in: int | None) -> int | None:
    """Convert an evaluation to a centipawn equivalent.

    Mate-in-N scores are mapped to large ± centipawn values so that
    centipawn loss can be computed even across mate boundaries.

    * mate_in > 0 (White mates): large positive value
    * mate_in < 0 (Black mates): large negative value
    * mate_in == 0 (checkmate on board): ``None`` — not useful for cp loss
    """
    if evaluation is not None:
        return evaluation
    if mate_in is not None and mate_in != 0:
        sign = 1 if mate_in > 0 else -1
        return sign * (_MATE_CP_BASE - abs(mate_in) * _MATE_CP_STEP)
    return None


def _compute_centipawn_loss(
    eval_before: PositionEvaluation,
    eval_after: PositionEvaluation,
    is_white: bool,
) -> int | None:
    """Compute centipawn loss for a half-move.

    Centipawn loss measures how much worse the played move is compared to
    the best available move, from the moving player's perspective.

    For White: ``cp_loss = best_eval − played_eval`` (White-perspective)
    For Black: ``cp_loss = played_eval − best_eval`` (White-perspective,
    inverted because Black wants a *lower* White-perspective score)

    Returns ``None`` when either evaluation is unavailable.  The result
    is clamped to a minimum of 0.
    """
    cp_before = _eval_to_cp(eval_before.evaluation, eval_before.mate_in)
    cp_after = _eval_to_cp(eval_after.evaluation, eval_after.mate_in)

    if cp_before is None or cp_after is None:
        return None

    if is_white:
        loss = cp_before - cp_after
    else:
        loss = cp_after - cp_before

    return max(0, loss)


def _candidate_to_dict(c) -> dict:
    """Serialise a :class:`CandidateMove` for JSON storage."""
    return {
        "move_san": c.move_san,
        "evaluation": c.evaluation,
        "mate_in": c.mate_in,
    }


def _insight_to_dict(insight) -> dict:
    """Serialise a :class:`LearningInsight` for JSON storage."""
    return {
        "move_number": insight.move_number,
        "is_white": insight.is_white,
        "played_move": insight.played_move,
        "best_move": insight.best_move,
        "centipawn_loss": insight.centipawn_loss,
        "classification": insight.classification.value,
        "principal_variation": insight.principal_variation,
        "explanation": insight.explanation,
    }


class ReviewEngine:
    """Orchestrates full game analysis using Stockfish.

    Accepts an active :class:`StockfishEngine` for position evaluation
    and an open SQLite connection for persistence.  Progress can be
    tracked via an optional callback for SSE streaming support.

    Args:
        stockfish_engine: An initialised Stockfish wrapper.
        db_conn: An open SQLite connection (schema already initialised).
        depth: Stockfish search depth in plies (minimum 20 per Req 5.1).
    """

    def __init__(
        self,
        stockfish_engine: StockfishEngine,
        db_conn: sqlite3.Connection,
        depth: int = 20,
    ) -> None:
        self._stockfish = stockfish_engine
        self._db = db_conn
        self._depth = max(depth, 20)  # enforce minimum depth (Req 5.1)

    def analyze_game(
        self,
        game_id: str,
        progress_callback: ProgressCallback | None = None,
    ) -> GameAnalysis:
        """Run full Stockfish analysis on a stored game.

        Loads the game from the database, evaluates every position at
        the configured search depth, classifies each move, computes
        per-player performance ratings, generates learning insights for
        suboptimal moves, and stores all results before returning the
        complete analysis.

        Args:
            game_id: Database identifier for the game.
            progress_callback: Optional callback invoked after each
                position is analysed, receiving
                ``(positions_analyzed, total_positions)``.

        Returns:
            A fully-populated :class:`GameAnalysis`.

        Raises:
            ValueError: If the game does not exist in the database.
        """
        # ------------------------------------------------------------------
        # 1. Load game from DB
        # ------------------------------------------------------------------
        game_data = get_game(self._db, game_id)
        if game_data is None:
            raise ValueError(f"Game not found: {game_id}")

        moves: list[str] = game_data["moves"]
        fens: list[str] = game_data["fens"]
        total_positions = len(moves)

        # Determine initial position (supports games from a custom FEN).
        initial_fen = game_data["additional_headers"].get(
            "FEN", chess.STARTING_FEN
        )

        # Full position list: initial position + FEN after each half-move.
        position_fens = [initial_fen] + fens

        # ------------------------------------------------------------------
        # 2. Evaluate initial position
        # ------------------------------------------------------------------
        prev_eval = self._stockfish.evaluate_position(
            initial_fen, depth=self._depth
        )

        # ------------------------------------------------------------------
        # 3. Iterate through each half-move
        # ------------------------------------------------------------------
        analyzed_moves: list[AnalyzedMove] = []
        evaluations: list[int | None] = []
        white_cp_losses: list[int] = []
        black_cp_losses: list[int] = []

        for i, move_san in enumerate(moves):
            is_white = i % 2 == 0
            move_number = (i // 2) + 1

            fen_before = position_fens[i]
            fen_after = position_fens[i + 1]

            # Evaluate the position *after* the move.
            eval_after = self._stockfish.evaluate_position(
                fen_after, depth=self._depth
            )

            # --- Handle error positions (Req 5.7) -------------------------
            if prev_eval.is_error or eval_after.is_error:
                analyzed_move = self._build_error_move(
                    move_number=move_number,
                    is_white=is_white,
                    move_san=move_san,
                    fen_before=fen_before,
                    fen_after=fen_after,
                    eval_before=prev_eval,
                    eval_after=eval_after,
                )
                analyzed_moves.append(analyzed_move)
                evaluations.append(None)

                self._store_move_result(game_id, i, analyzed_move)

                prev_eval = eval_after
                if progress_callback:
                    progress_callback(i + 1, total_positions)
                continue

            # --- Centipawn loss and classification -------------------------
            cp_loss = _compute_centipawn_loss(prev_eval, eval_after, is_white)
            classification = classify_move_safe(cp_loss)

            # Candidate moves come from the position *before* the move.
            candidates = prev_eval.candidate_moves

            # --- Learning insight for suboptimal moves (Req 9.1) -----------
            insight = None
            if (
                classification is not None
                and classification in _INSIGHT_CLASSIFICATIONS
                and cp_loss is not None
            ):
                best_move = candidates[0].move_san if candidates else ""
                # Use candidate-move list as a proxy for the PV.
                principal_variation = [c.move_san for c in candidates]
                insight = generate_insight(
                    move_number=move_number,
                    is_white=is_white,
                    played_move=move_san,
                    best_move=best_move,
                    centipawn_loss=cp_loss,
                    classification=classification,
                    principal_variation=principal_variation,
                )

            # --- Track centipawn losses per player (Req 8.1) ---------------
            if cp_loss is not None:
                if is_white:
                    white_cp_losses.append(cp_loss)
                else:
                    black_cp_losses.append(cp_loss)

            # --- Build AnalyzedMove ----------------------------------------
            analyzed_move = AnalyzedMove(
                move_number=move_number,
                is_white=is_white,
                move_san=move_san,
                position_before=fen_before,
                position_after=fen_after,
                evaluation_before=prev_eval,
                evaluation_after=eval_after,
                classification=classification,
                centipawn_loss=cp_loss,
                candidate_moves=candidates,
                insight=insight,
            )
            analyzed_moves.append(analyzed_move)

            # Evaluation for the graph (centipawn after this move).
            graph_eval = _eval_to_cp(
                eval_after.evaluation, eval_after.mate_in
            )
            evaluations.append(graph_eval)

            # --- Persist per-move result -----------------------------------
            self._store_move_result(game_id, i, analyzed_move)

            prev_eval = eval_after
            if progress_callback:
                progress_callback(i + 1, total_positions)

        # ------------------------------------------------------------------
        # 4. Compute per-player summaries (Reqs 6.4, 8.1)
        # ------------------------------------------------------------------
        white_summary = self._build_player_summary(
            analyzed_moves, white_cp_losses, is_white=True
        )
        black_summary = self._build_player_summary(
            analyzed_moves, black_cp_losses, is_white=False
        )

        # ------------------------------------------------------------------
        # 5. Store analysis summary
        # ------------------------------------------------------------------
        upsert_analysis_summary(
            self._db,
            game_id=game_id,
            is_complete=True,
            white_summary=white_summary,
            black_summary=black_summary,
        )

        # ------------------------------------------------------------------
        # 6. Return complete analysis
        # ------------------------------------------------------------------
        return GameAnalysis(
            game_id=game_id,
            moves=analyzed_moves,
            white_summary=white_summary,
            black_summary=black_summary,
            evaluations=evaluations,
            is_complete=True,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_error_move(
        *,
        move_number: int,
        is_white: bool,
        move_san: str,
        fen_before: str,
        fen_after: str,
        eval_before: PositionEvaluation,
        eval_after: PositionEvaluation,
    ) -> AnalyzedMove:
        """Build an AnalyzedMove for positions that could not be evaluated."""
        return AnalyzedMove(
            move_number=move_number,
            is_white=is_white,
            move_san=move_san,
            position_before=fen_before,
            position_after=fen_after,
            evaluation_before=eval_before,
            evaluation_after=eval_after,
            classification=None,
            centipawn_loss=None,
            candidate_moves=(
                eval_before.candidate_moves
                if not eval_before.is_error
                else []
            ),
            insight=None,
        )

    @staticmethod
    def _build_player_summary(
        analyzed_moves: list[AnalyzedMove],
        cp_losses: list[int],
        *,
        is_white: bool,
    ) -> PlayerAnalysisSummary:
        """Compute the per-player classification counts and ratings."""
        counts = compute_classification_summary(analyzed_moves, is_white)
        cumulative_ratings = compute_cumulative_ratings(cp_losses)
        final_rating = compute_performance_rating(cp_losses)

        return PlayerAnalysisSummary(
            best_count=counts["best"],
            excellent_count=counts["excellent"],
            good_count=counts["good"],
            inaccuracy_count=counts["inaccuracy"],
            mistake_count=counts["mistake"],
            blunder_count=counts["blunder"],
            performance_ratings=cumulative_ratings,
            final_performance_rating=final_rating,
        )

    def _store_move_result(
        self,
        game_id: str,
        move_index: int,
        move: AnalyzedMove,
    ) -> None:
        """Persist a single move's analysis result to the database."""
        insert_analysis_result(
            conn=self._db,
            game_id=game_id,
            move_index=move_index,
            is_white=move.is_white,
            move_san=move.move_san,
            fen_before=move.position_before,
            fen_after=move.position_after,
            eval_before=move.evaluation_before.evaluation,
            mate_before=move.evaluation_before.mate_in,
            eval_after=move.evaluation_after.evaluation,
            mate_after=move.evaluation_after.mate_in,
            classification=(
                move.classification.value if move.classification else None
            ),
            centipawn_loss=move.centipawn_loss,
            candidate_moves=[
                _candidate_to_dict(c) for c in move.candidate_moves
            ],
            insight=(
                _insight_to_dict(move.insight) if move.insight else None
            ),
        )
