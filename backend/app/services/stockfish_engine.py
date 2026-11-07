"""Stockfish UCI engine interface via python-chess.

Wraps chess.engine.SimpleEngine to evaluate positions, returning centipawn
scores from White's perspective, mate-in-N indicators, and ranked candidate
moves via MultiPV analysis.
"""

from __future__ import annotations

import logging
import os

import chess
import chess.engine

from app.models import CandidateMove, PositionEvaluation

logger = logging.getLogger(__name__)

# Default Stockfish binary path, overridable via environment variable.
DEFAULT_STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH", "stockfish")


class StockfishEngine:
    """Manages a Stockfish UCI subprocess for position evaluation.

    The engine is lazily started on the first call to evaluate_position()
    and reused across analyses. If the engine process terminates unexpectedly,
    it is automatically restarted on the next evaluation call.
    """

    def __init__(self, stockfish_path: str | None = None) -> None:
        self._path = stockfish_path or DEFAULT_STOCKFISH_PATH
        self._engine: chess.engine.SimpleEngine | None = None

    @property
    def is_running(self) -> bool:
        """Return True if the engine subprocess is alive."""
        if self._engine is None:
            return False
        # python-chess stores the transport; check if the process is alive
        try:
            transport = self._engine.transport
            returncode = transport.get_returncode()
            return returncode is None
        except Exception:
            return False

    def start(self) -> None:
        """Start (or restart) the Stockfish engine subprocess."""
        self.stop()
        logger.info("Starting Stockfish engine at %s", self._path)
        self._engine = chess.engine.SimpleEngine.popen_uci(self._path)
        logger.info("Stockfish engine started successfully")

    def stop(self) -> None:
        """Gracefully shut down the engine subprocess if running."""
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                # Engine may already be dead; ignore errors during shutdown.
                pass
            self._engine = None

    def _ensure_engine(self) -> None:
        """Ensure the engine is running, restarting if necessary."""
        if not self.is_running:
            self.start()

    def evaluate_position(
        self,
        fen: str,
        depth: int = 20,
        multi_pv: int = 3,
    ) -> PositionEvaluation:
        """Evaluate a chess position and return ranked candidate moves.

        Args:
            fen: Position in FEN notation.
            depth: Search depth in plies (minimum 20 per requirements).
            multi_pv: Number of principal variations to compute (up to 3).

        Returns:
            PositionEvaluation with centipawn score from White's perspective,
            mate-in-N indicator, and up to ``multi_pv`` candidate moves.
            If the FEN is invalid, returns an error evaluation instead of
            raising an exception.
        """
        # Validate the FEN and build a board.
        try:
            board = chess.Board(fen)
        except ValueError as exc:
            logger.warning("Invalid FEN '%s': %s", fen, exc)
            return PositionEvaluation(
                fen=fen,
                evaluation=None,
                mate_in=None,
                candidate_moves=[],
                is_error=True,
            )

        # If the position is already game-over (checkmate / stalemate),
        # return immediately without querying the engine.
        if board.is_game_over():
            evaluation, mate_in = self._game_over_score(board)
            return PositionEvaluation(
                fen=fen,
                evaluation=evaluation,
                mate_in=mate_in,
                candidate_moves=[],
            )

        # Make sure the engine is running (lazy start / restart after crash).
        try:
            self._ensure_engine()
        except Exception as exc:
            logger.error("Failed to start Stockfish engine: %s", exc)
            return PositionEvaluation(
                fen=fen,
                evaluation=None,
                mate_in=None,
                candidate_moves=[],
                is_error=True,
            )

        # Clamp multi_pv to the number of legal moves.
        legal_move_count = sum(1 for _ in board.legal_moves)
        effective_multi_pv = min(multi_pv, legal_move_count)
        if effective_multi_pv < 1:
            effective_multi_pv = 1

        # Run the analysis.
        try:
            results = self._engine.analyse(
                board,
                chess.engine.Limit(depth=depth),
                multipv=effective_multi_pv,
            )
        except chess.engine.EngineTerminatedError:
            logger.warning("Stockfish terminated unexpectedly; restarting")
            self._engine = None
            try:
                self._ensure_engine()
                results = self._engine.analyse(
                    board,
                    chess.engine.Limit(depth=depth),
                    multipv=effective_multi_pv,
                )
            except Exception as exc:
                logger.error("Engine restart failed during analysis: %s", exc)
                return PositionEvaluation(
                    fen=fen,
                    evaluation=None,
                    mate_in=None,
                    candidate_moves=[],
                    is_error=True,
                )
        except Exception as exc:
            logger.error("Stockfish analysis failed for FEN '%s': %s", fen, exc)
            return PositionEvaluation(
                fen=fen,
                evaluation=None,
                mate_in=None,
                candidate_moves=[],
                is_error=True,
            )

        # When multipv > 1, python-chess returns a list of info dicts.
        # When multipv == 1, it returns a single dict — normalise to a list.
        if isinstance(results, dict):
            results = [results]

        # Build candidate moves from multi-PV results.
        candidate_moves: list[CandidateMove] = []
        top_evaluation: int | None = None
        top_mate_in: int | None = None

        for idx, info in enumerate(results):
            score: chess.engine.PovScore | None = info.get("score")
            pv: list[chess.Move] | None = info.get("pv")

            cp_value: int | None = None
            mate_value: int | None = None

            if score is not None:
                white_score = score.white()
                if white_score.is_mate():
                    mate_value = white_score.mate()
                else:
                    cp_value = white_score.score()

            # First PV is the top evaluation for the position.
            if idx == 0:
                top_evaluation = cp_value
                top_mate_in = mate_value

            # Convert the first move of the PV to SAN.
            if pv and len(pv) > 0:
                try:
                    move_san = board.san(pv[0])
                except Exception:
                    move_san = pv[0].uci()
                candidate_moves.append(
                    CandidateMove(
                        move_san=move_san,
                        evaluation=cp_value,
                        mate_in=mate_value,
                    )
                )

        return PositionEvaluation(
            fen=fen,
            evaluation=top_evaluation,
            mate_in=top_mate_in,
            candidate_moves=candidate_moves,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _game_over_score(
        board: chess.Board,
    ) -> tuple[int | None, int | None]:
        """Return (evaluation, mate_in) for a terminal position."""
        if board.is_checkmate():
            # Side to move is checkmated → the *other* side wins.
            if board.turn == chess.WHITE:
                # White is checkmated → Black wins.
                return None, 0  # mate_in 0 from losing side's perspective
            else:
                # Black is checkmated → White wins.
                return None, 0
        # Stalemate / draw.
        return 0, None

    def __del__(self) -> None:
        self.stop()
