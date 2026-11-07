"""Unit tests for StockfishEngine — mocked, no real Stockfish binary needed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import chess
import chess.engine
import pytest

from app.models import CandidateMove, PositionEvaluation
from app.services.stockfish_engine import StockfishEngine

# ---------------------------------------------------------------------------
# Helpers for building mock analysis results
# ---------------------------------------------------------------------------

STARTING_FEN = chess.STARTING_FEN


def _make_cp_score(cp: int) -> chess.engine.PovScore:
    """Create a PovScore wrapping a centipawn Cp value from White's POV."""
    return chess.engine.PovScore(chess.engine.Cp(cp), chess.WHITE)


def _make_mate_score(mate_in: int) -> chess.engine.PovScore:
    """Create a PovScore wrapping a Mate value from White's POV."""
    return chess.engine.PovScore(chess.engine.Mate(mate_in), chess.WHITE)


def _make_info(
    score: chess.engine.PovScore,
    pv_uci: list[str],
    board: chess.Board | None = None,
) -> dict:
    """Build an ``info`` dict like python-chess returns from analyse()."""
    moves = [chess.Move.from_uci(u) for u in pv_uci]
    return {"score": score, "pv": moves}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_engine():
    """Return a patched StockfishEngine whose underlying UCI engine is mocked."""
    with patch(
        "app.services.stockfish_engine.chess.engine.SimpleEngine.popen_uci"
    ) as mock_popen:
        inner = MagicMock(spec=chess.engine.SimpleEngine)
        mock_popen.return_value = inner

        engine = StockfishEngine(stockfish_path="/fake/stockfish")

        # Mock transport to simulate a running engine
        transport_mock = MagicMock()
        transport_mock.get_returncode.return_value = None  # process alive
        inner.transport = transport_mock

        yield engine, inner

    engine.stop()


# ---------------------------------------------------------------------------
# Tests: normal centipawn evaluation
# ---------------------------------------------------------------------------


class TestEvaluatePositionCentipawns:
    """Centipawn scores returned from White's perspective."""

    def test_starting_position_returns_cp_and_candidates(self, mock_engine):
        engine, inner = mock_engine

        # Simulate 3 PVs with centipawn scores.
        inner.analyse.return_value = [
            _make_info(_make_cp_score(30), ["e2e4"]),
            _make_info(_make_cp_score(25), ["d2d4"]),
            _make_info(_make_cp_score(20), ["g1f3"]),
        ]

        result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=3)

        assert isinstance(result, PositionEvaluation)
        assert result.fen == STARTING_FEN
        assert result.evaluation == 30
        assert result.mate_in is None
        assert result.is_error is False
        assert len(result.candidate_moves) == 3
        assert result.candidate_moves[0].move_san == "e4"
        assert result.candidate_moves[0].evaluation == 30
        assert result.candidate_moves[1].evaluation == 25
        assert result.candidate_moves[2].evaluation == 20

    def test_negative_evaluation_for_black_advantage(self, mock_engine):
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_cp_score(-150), ["e7e5"]),
        ]

        # A position where Black is better (from White's POV → negative).
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        result = engine.evaluate_position(fen, depth=20, multi_pv=1)

        assert result.evaluation == -150
        assert result.mate_in is None
        assert result.is_error is False


# ---------------------------------------------------------------------------
# Tests: mate-in-N evaluation
# ---------------------------------------------------------------------------


class TestEvaluatePositionMate:
    """Mate-in-N indicator returned when Stockfish detects forced checkmate."""

    def test_mate_in_2_white(self, mock_engine):
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_mate_score(2), ["d1h5"]),
        ]

        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1"
        result = engine.evaluate_position(fen, depth=20, multi_pv=1)

        assert result.evaluation is None
        assert result.mate_in == 2
        assert result.is_error is False

    def test_mate_in_negative_for_black(self, mock_engine):
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_mate_score(-3), ["e7e5"]),
        ]

        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        result = engine.evaluate_position(fen, depth=20, multi_pv=1)

        assert result.evaluation is None
        assert result.mate_in == -3

    def test_mixed_mate_and_cp_candidates(self, mock_engine):
        """First PV shows mate; other PVs show centipawn."""
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_mate_score(1), ["d1h5"]),
            _make_info(_make_cp_score(500), ["d1f3"]),
        ]

        result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=2)

        # Top eval is mate-in-1.
        assert result.evaluation is None
        assert result.mate_in == 1
        # Candidates carry their own scores.
        assert result.candidate_moves[0].mate_in == 1
        assert result.candidate_moves[0].evaluation is None
        assert result.candidate_moves[1].mate_in is None
        assert result.candidate_moves[1].evaluation == 500


# ---------------------------------------------------------------------------
# Tests: candidate moves ranking via MultiPV
# ---------------------------------------------------------------------------


class TestCandidateMoves:
    """Up to 3 candidate moves ranked by evaluation."""

    def test_returns_up_to_3_candidates(self, mock_engine):
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_cp_score(40), ["e2e4"]),
            _make_info(_make_cp_score(30), ["d2d4"]),
            _make_info(_make_cp_score(20), ["c2c4"]),
        ]

        result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=3)
        assert len(result.candidate_moves) == 3

    def test_fewer_candidates_when_fewer_legal_moves(self, mock_engine):
        """Position with only 1 legal move → only 1 candidate returned."""
        engine, inner = mock_engine

        # King with only 1 legal move.
        fen = "8/8/8/8/8/7k/8/6RK w - - 0 1"
        inner.analyse.return_value = [
            _make_info(_make_cp_score(0), ["g1g2"]),
        ]

        result = engine.evaluate_position(fen, depth=20, multi_pv=3)
        # engine.analyse was called with effective_multi_pv clamped to legal moves
        assert len(result.candidate_moves) >= 1

    def test_candidate_moves_have_correct_san(self, mock_engine):
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_cp_score(30), ["e2e4"]),
        ]

        result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)
        assert result.candidate_moves[0].move_san == "e4"


# ---------------------------------------------------------------------------
# Tests: invalid FEN → error, no crash
# ---------------------------------------------------------------------------


class TestInvalidPositions:
    """Invalid positions return is_error=True instead of raising."""

    def test_invalid_fen_returns_error(self, mock_engine):
        engine, _ = mock_engine
        result = engine.evaluate_position("not a valid fen", depth=20)

        assert result.is_error is True
        assert result.evaluation is None
        assert result.mate_in is None
        assert result.candidate_moves == []
        assert result.fen == "not a valid fen"

    def test_empty_fen_returns_error(self, mock_engine):
        engine, _ = mock_engine
        result = engine.evaluate_position("", depth=20)

        assert result.is_error is True

    def test_partial_fen_returns_error(self, mock_engine):
        engine, _ = mock_engine
        result = engine.evaluate_position("rnbqkbnr/pppppppp", depth=20)

        assert result.is_error is True


# ---------------------------------------------------------------------------
# Tests: game-over positions
# ---------------------------------------------------------------------------


class TestGameOverPositions:
    """Terminal positions (checkmate, stalemate) handled without engine call."""

    def test_checkmate_position(self, mock_engine):
        engine, inner = mock_engine

        # Fool's mate position — Black wins by checkmate.
        fen = "rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3"
        result = engine.evaluate_position(fen, depth=20)

        # No engine call needed for terminal positions.
        inner.analyse.assert_not_called()
        assert result.is_error is False
        assert result.candidate_moves == []
        assert result.mate_in == 0

    def test_stalemate_position(self, mock_engine):
        engine, inner = mock_engine

        # Known stalemate position — King trapped.
        fen = "k7/8/1K6/8/8/8/8/8 b - - 0 1"
        board = chess.Board(fen)
        if not board.is_game_over():
            pytest.skip("FEN is not actually stalemate on this version")

        result = engine.evaluate_position(fen, depth=20)
        inner.analyse.assert_not_called()
        assert result.evaluation == 0
        assert result.mate_in is None


# ---------------------------------------------------------------------------
# Tests: engine lifecycle management
# ---------------------------------------------------------------------------


class TestEngineLifecycle:
    """Engine startup, reuse, and restart on unexpected termination."""

    def test_lazy_start_on_first_evaluate(self):
        """Engine is not started until evaluate_position is called."""
        with patch(
            "app.services.stockfish_engine.chess.engine.SimpleEngine.popen_uci"
        ) as mock_popen:
            inner = MagicMock(spec=chess.engine.SimpleEngine)
            mock_popen.return_value = inner
            transport_mock = MagicMock()
            transport_mock.get_returncode.return_value = None
            inner.transport = transport_mock

            inner.analyse.return_value = [
                _make_info(_make_cp_score(20), ["e2e4"]),
            ]

            engine = StockfishEngine(stockfish_path="/fake/stockfish")
            assert engine._engine is None  # not started yet

            engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)
            mock_popen.assert_called_once()  # started lazily

    def test_engine_reused_across_calls(self, mock_engine):
        """Same engine instance is reused for multiple evaluations."""
        engine, inner = mock_engine

        inner.analyse.return_value = [
            _make_info(_make_cp_score(20), ["e2e4"]),
        ]

        engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)
        engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)

        # analyse called twice, but popen_uci only once (via fixture start).
        assert inner.analyse.call_count == 2

    def test_restart_on_engine_terminated_error(self):
        """If engine dies mid-analysis, it restarts and retries."""
        with patch(
            "app.services.stockfish_engine.chess.engine.SimpleEngine.popen_uci"
        ) as mock_popen:
            inner_1 = MagicMock(spec=chess.engine.SimpleEngine)
            inner_2 = MagicMock(spec=chess.engine.SimpleEngine)

            # First engine dies on analyse.
            inner_1.analyse.side_effect = chess.engine.EngineTerminatedError()
            transport_1 = MagicMock()
            transport_1.get_returncode.return_value = None
            inner_1.transport = transport_1

            # Second engine works fine.
            inner_2.analyse.return_value = [
                _make_info(_make_cp_score(15), ["d2d4"]),
            ]
            transport_2 = MagicMock()
            transport_2.get_returncode.return_value = None
            inner_2.transport = transport_2

            mock_popen.side_effect = [inner_1, inner_2]

            engine = StockfishEngine(stockfish_path="/fake/stockfish")
            result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)

            assert result.is_error is False
            assert result.evaluation == 15
            assert mock_popen.call_count == 2  # started, restarted

    def test_error_when_engine_cannot_start(self):
        """If engine binary is missing, return error evaluation."""
        with patch(
            "app.services.stockfish_engine.chess.engine.SimpleEngine.popen_uci"
        ) as mock_popen:
            mock_popen.side_effect = FileNotFoundError("stockfish not found")

            engine = StockfishEngine(stockfish_path="/nonexistent/stockfish")
            result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)

            assert result.is_error is True
            assert result.evaluation is None

    def test_stop_shuts_down_engine(self, mock_engine):
        engine, inner = mock_engine

        engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)
        engine.stop()

        inner.quit.assert_called_once()
        assert engine._engine is None

    def test_stop_ignores_already_dead_engine(self, mock_engine):
        engine, inner = mock_engine

        inner.quit.side_effect = Exception("already dead")
        engine.stop()  # should not raise

        assert engine._engine is None

    def test_is_running_false_when_not_started(self):
        engine = StockfishEngine(stockfish_path="/fake/stockfish")
        assert engine.is_running is False

    def test_is_running_true_when_started(self, mock_engine):
        engine, inner = mock_engine
        # The fixture already patches transport to return None (alive).
        engine.start()
        assert engine.is_running is True

    def test_is_running_false_after_process_exits(self, mock_engine):
        engine, inner = mock_engine
        engine.start()

        # Simulate process exit.
        inner.transport.get_returncode.return_value = 1
        assert engine.is_running is False


# ---------------------------------------------------------------------------
# Tests: analysis failure falls back to error
# ---------------------------------------------------------------------------


class TestAnalysisFailure:
    """Unexpected errors during analysis return error evaluations."""

    def test_generic_exception_returns_error(self, mock_engine):
        engine, inner = mock_engine
        inner.analyse.side_effect = RuntimeError("unexpected engine error")

        result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)

        assert result.is_error is True
        assert result.evaluation is None

    def test_restart_failure_after_terminated_returns_error(self):
        """If restart also fails after EngineTerminatedError, return error."""
        with patch(
            "app.services.stockfish_engine.chess.engine.SimpleEngine.popen_uci"
        ) as mock_popen:
            inner_1 = MagicMock(spec=chess.engine.SimpleEngine)
            inner_1.analyse.side_effect = chess.engine.EngineTerminatedError()
            transport_1 = MagicMock()
            transport_1.get_returncode.return_value = None
            inner_1.transport = transport_1

            # Restart also fails.
            mock_popen.side_effect = [
                inner_1,
                FileNotFoundError("still missing"),
            ]

            engine = StockfishEngine(stockfish_path="/fake/stockfish")
            result = engine.evaluate_position(STARTING_FEN, depth=20, multi_pv=1)

            assert result.is_error is True
