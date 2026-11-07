"""Unit tests for ReviewEngine — mocked Stockfish, in-memory SQLite."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import chess
import pytest

from app.database import (
    SCHEMA_SQL,
    get_analysis,
    get_analysis_summary,
    get_connection,
    insert_game,
)
from app.models import (
    AnalyzedMove,
    CandidateMove,
    GameAnalysis,
    MoveClassification,
    ParsedGame,
    PlayerAnalysisSummary,
    PositionEvaluation,
)
from app.services.review_engine import (
    ReviewEngine,
    _compute_centipawn_loss,
    _eval_to_cp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_eval(
    fen: str,
    cp: int | None = None,
    mate: int | None = None,
    candidates: list[CandidateMove] | None = None,
    is_error: bool = False,
) -> PositionEvaluation:
    """Build a PositionEvaluation for testing."""
    return PositionEvaluation(
        fen=fen,
        evaluation=cp,
        mate_in=mate,
        candidate_moves=candidates or [],
        is_error=is_error,
    )


# A simple 4-move game: 1. e4 e5 2. Nf3 d6
SAMPLE_MOVES = ["e4", "e5", "Nf3", "d6"]
SAMPLE_FENS = [
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
    "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn():
    """In-memory SQLite connection with schema initialised."""
    conn = get_connection(":memory:")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_game() -> ParsedGame:
    return ParsedGame(
        event="Test",
        site="Test",
        date="2024.01.01",
        round="-",
        white="white_player",
        black="black_player",
        result="1-0",
        moves=SAMPLE_MOVES,
        fens=SAMPLE_FENS,
    )


@pytest.fixture
def game_in_db(db_conn, sample_game):
    """Insert the sample game and return its ID."""
    game_id = "test-game-1"
    insert_game(db_conn, game_id, "testuser", "1. e4 e5 ...", sample_game)
    return game_id


@pytest.fixture
def mock_stockfish():
    """A mock StockfishEngine returning centipawn evals."""
    engine = MagicMock()

    # Default: return +20 cp for any FEN with one candidate.
    def default_eval(fen, depth=20, multi_pv=3):
        return _make_eval(
            fen,
            cp=20,
            candidates=[CandidateMove(move_san="e4", evaluation=20, mate_in=None)],
        )

    engine.evaluate_position = MagicMock(side_effect=default_eval)
    return engine


# ---------------------------------------------------------------------------
# Tests: _eval_to_cp helper
# ---------------------------------------------------------------------------


class TestEvalToCp:
    def test_centipawn_value(self):
        assert _eval_to_cp(150, None) == 150

    def test_negative_centipawn(self):
        assert _eval_to_cp(-200, None) == -200

    def test_mate_positive(self):
        result = _eval_to_cp(None, 3)
        assert result > 0
        assert result == 10000 - 30

    def test_mate_negative(self):
        result = _eval_to_cp(None, -5)
        assert result < 0
        assert result == -(10000 - 50)

    def test_mate_zero_returns_none(self):
        assert _eval_to_cp(None, 0) is None

    def test_both_none_returns_none(self):
        assert _eval_to_cp(None, None) is None

    def test_centipawn_takes_precedence(self):
        # If both are set, centipawn wins (shouldn't happen but test anyway)
        assert _eval_to_cp(100, 3) == 100


# ---------------------------------------------------------------------------
# Tests: _compute_centipawn_loss helper
# ---------------------------------------------------------------------------


class TestComputeCentipawnLoss:
    def test_white_no_loss(self):
        before = _make_eval("fen", cp=30)
        after = _make_eval("fen", cp=30)
        assert _compute_centipawn_loss(before, after, is_white=True) == 0

    def test_white_with_loss(self):
        before = _make_eval("fen", cp=50)
        after = _make_eval("fen", cp=20)
        assert _compute_centipawn_loss(before, after, is_white=True) == 30

    def test_white_negative_loss_clamped(self):
        # Played a move that improved eval (impossible in theory, but clamp)
        before = _make_eval("fen", cp=20)
        after = _make_eval("fen", cp=50)
        assert _compute_centipawn_loss(before, after, is_white=True) == 0

    def test_black_no_loss(self):
        before = _make_eval("fen", cp=-30)
        after = _make_eval("fen", cp=-30)
        assert _compute_centipawn_loss(before, after, is_white=False) == 0

    def test_black_with_loss(self):
        # From White's perspective: before was -50, after is -20.
        # Black wanted it more negative; loss = (-20) - (-50) = 30
        before = _make_eval("fen", cp=-50)
        after = _make_eval("fen", cp=-20)
        assert _compute_centipawn_loss(before, after, is_white=False) == 30

    def test_returns_none_when_before_missing(self):
        before = _make_eval("fen", cp=None, mate=None)
        after = _make_eval("fen", cp=30)
        assert _compute_centipawn_loss(before, after, is_white=True) is None

    def test_returns_none_when_after_missing(self):
        before = _make_eval("fen", cp=30)
        after = _make_eval("fen", cp=None, mate=None)
        assert _compute_centipawn_loss(before, after, is_white=True) is None

    def test_mate_to_cp_transition(self):
        # Before: White has mate in 5; After: only +300 cp
        before = _make_eval("fen", mate=5)  # ≈ 9950
        after = _make_eval("fen", cp=300)
        loss = _compute_centipawn_loss(before, after, is_white=True)
        assert loss is not None
        assert loss > 0


# ---------------------------------------------------------------------------
# Tests: analyze_game happy path
# ---------------------------------------------------------------------------


class TestAnalyzeGameHappyPath:
    def test_returns_game_analysis(self, db_conn, game_in_db, mock_stockfish):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        assert isinstance(result, GameAnalysis)
        assert result.game_id == game_in_db
        assert result.is_complete is True

    def test_correct_number_of_analyzed_moves(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        assert len(result.moves) == len(SAMPLE_MOVES)

    def test_evaluations_list_populated(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        assert len(result.evaluations) == len(SAMPLE_MOVES)

    def test_white_and_black_summaries_present(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        assert isinstance(result.white_summary, PlayerAnalysisSummary)
        assert isinstance(result.black_summary, PlayerAnalysisSummary)

    def test_stockfish_called_for_each_position(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        engine.analyze_game(game_in_db)

        # Initial position + 4 positions after each move = 5 calls.
        assert mock_stockfish.evaluate_position.call_count == 5

    def test_move_attributes_correct(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        # First move: e4 by White, move 1
        m = result.moves[0]
        assert m.move_san == "e4"
        assert m.is_white is True
        assert m.move_number == 1
        assert m.position_before == chess.STARTING_FEN
        assert m.position_after == SAMPLE_FENS[0]

        # Second move: e5 by Black, move 1
        m = result.moves[1]
        assert m.move_san == "e5"
        assert m.is_white is False
        assert m.move_number == 1

        # Third move: Nf3 by White, move 2
        m = result.moves[2]
        assert m.move_san == "Nf3"
        assert m.is_white is True
        assert m.move_number == 2


# ---------------------------------------------------------------------------
# Tests: move classification
# ---------------------------------------------------------------------------


class TestMoveClassification:
    def test_all_perfect_moves_classified_best(
        self, db_conn, game_in_db
    ):
        """When eval never changes, cp_loss=0 → all classified BEST."""
        mock_sf = MagicMock()
        mock_sf.evaluate_position = MagicMock(
            side_effect=lambda fen, depth=20, multi_pv=3: _make_eval(
                fen,
                cp=30,
                candidates=[
                    CandidateMove(move_san="e4", evaluation=30, mate_in=None)
                ],
            )
        )

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        for m in result.moves:
            assert m.classification == MoveClassification.BEST
            assert m.centipawn_loss == 0

    def test_blunder_classified_correctly(self, db_conn, game_in_db):
        """A big eval drop from the player's perspective → blunder."""
        mock_sf = MagicMock()

        evals = iter(
            [
                _make_eval(chess.STARTING_FEN, cp=30, candidates=[
                    CandidateMove(move_san="e4", evaluation=30, mate_in=None)
                ]),
                # After move 1 (e4 by White): eval drops significantly
                _make_eval(SAMPLE_FENS[0], cp=-200, candidates=[]),
                # Remaining positions
                _make_eval(SAMPLE_FENS[1], cp=-200, candidates=[
                    CandidateMove(move_san="Nf6", evaluation=-200, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[2], cp=-200, candidates=[]),
                _make_eval(SAMPLE_FENS[3], cp=-200, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        # First move by White: before=+30, after=-200 → loss=230 → blunder
        assert result.moves[0].classification == MoveClassification.BLUNDER
        assert result.moves[0].centipawn_loss == 230


# ---------------------------------------------------------------------------
# Tests: insights for suboptimal moves
# ---------------------------------------------------------------------------


class TestInsightGeneration:
    def test_insight_generated_for_blunder(self, db_conn, game_in_db):
        mock_sf = MagicMock()

        evals = iter(
            [
                _make_eval(chess.STARTING_FEN, cp=30, candidates=[
                    CandidateMove(move_san="d4", evaluation=35, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[0], cp=-200, candidates=[]),
                _make_eval(SAMPLE_FENS[1], cp=-200, candidates=[
                    CandidateMove(move_san="Nf6", evaluation=-200, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[2], cp=-200, candidates=[]),
                _make_eval(SAMPLE_FENS[3], cp=-200, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        insight = result.moves[0].insight
        assert insight is not None
        assert insight.classification == MoveClassification.BLUNDER
        assert insight.centipawn_loss == 230
        assert insight.best_move == "d4"
        assert insight.played_move == "e4"

    def test_no_insight_for_good_moves(self, db_conn, game_in_db, mock_stockfish):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        for m in result.moves:
            assert m.insight is None  # All moves are "best" with constant eval


# ---------------------------------------------------------------------------
# Tests: performance ratings
# ---------------------------------------------------------------------------


class TestPerformanceRatings:
    def test_perfect_play_gives_max_rating(
        self, db_conn, game_in_db, mock_stockfish
    ):
        """All moves with 0 cp_loss → maximum performance rating."""
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        assert result.white_summary.final_performance_rating == 3000
        assert result.black_summary.final_performance_rating == 3000

    def test_cumulative_ratings_length(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        # 4 half-moves: 2 White, 2 Black
        assert len(result.white_summary.performance_ratings) == 2
        assert len(result.black_summary.performance_ratings) == 2

    def test_ratings_in_valid_range(self, db_conn, game_in_db):
        mock_sf = MagicMock()

        # Varying evaluations to produce non-zero cp losses
        evals = iter(
            [
                _make_eval(chess.STARTING_FEN, cp=30, candidates=[
                    CandidateMove(move_san="e4", evaluation=30, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[0], cp=10, candidates=[
                    CandidateMove(move_san="e5", evaluation=10, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[1], cp=15, candidates=[
                    CandidateMove(move_san="Nf3", evaluation=15, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[2], cp=5, candidates=[
                    CandidateMove(move_san="d6", evaluation=5, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[3], cp=8, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        for r in result.white_summary.performance_ratings:
            assert 0 <= r <= 3000
        for r in result.black_summary.performance_ratings:
            assert 0 <= r <= 3000


# ---------------------------------------------------------------------------
# Tests: error position handling (Req 5.7)
# ---------------------------------------------------------------------------


class TestErrorPositionHandling:
    def test_error_position_skipped_and_marked(self, db_conn, game_in_db):
        mock_sf = MagicMock()

        evals = iter(
            [
                # Initial position — OK
                _make_eval(chess.STARTING_FEN, cp=30, candidates=[
                    CandidateMove(move_san="e4", evaluation=30, mate_in=None)
                ]),
                # After move 1 — ERROR
                _make_eval(SAMPLE_FENS[0], is_error=True),
                # After move 2 — OK (but prev was error)
                _make_eval(SAMPLE_FENS[1], cp=15, candidates=[
                    CandidateMove(move_san="Nf3", evaluation=15, mate_in=None)
                ]),
                # After move 3 — OK
                _make_eval(SAMPLE_FENS[2], cp=10, candidates=[]),
                # After move 4 — OK
                _make_eval(SAMPLE_FENS[3], cp=10, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        assert len(result.moves) == 4
        # Move 1: eval_after is error → no classification
        assert result.moves[0].classification is None
        assert result.moves[0].centipawn_loss is None
        assert result.evaluations[0] is None

        # Move 2: prev_eval (the error one) is the eval_before → also no classification
        assert result.moves[1].classification is None

    def test_analysis_continues_after_error(self, db_conn, game_in_db):
        mock_sf = MagicMock()

        evals = iter(
            [
                _make_eval(chess.STARTING_FEN, cp=30, candidates=[
                    CandidateMove(move_san="e4", evaluation=30, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[0], is_error=True),
                _make_eval(SAMPLE_FENS[1], cp=15, candidates=[]),
                _make_eval(SAMPLE_FENS[2], cp=10, candidates=[]),
                _make_eval(SAMPLE_FENS[3], cp=10, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        # All 4 moves analysed despite the error
        assert len(result.moves) == 4
        assert result.is_complete is True


# ---------------------------------------------------------------------------
# Tests: progress callback
# ---------------------------------------------------------------------------


class TestProgressCallback:
    def test_callback_invoked_for_each_position(
        self, db_conn, game_in_db, mock_stockfish
    ):
        callback = MagicMock()
        engine = ReviewEngine(mock_stockfish, db_conn)
        engine.analyze_game(game_in_db, progress_callback=callback)

        assert callback.call_count == 4
        callback.assert_any_call(1, 4)
        callback.assert_any_call(2, 4)
        callback.assert_any_call(3, 4)
        callback.assert_any_call(4, 4)

    def test_no_error_when_callback_is_none(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db, progress_callback=None)
        assert result.is_complete is True


# ---------------------------------------------------------------------------
# Tests: database persistence
# ---------------------------------------------------------------------------


class TestDatabasePersistence:
    def test_analysis_results_stored(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        engine.analyze_game(game_in_db)

        results = get_analysis(db_conn, game_in_db)
        assert len(results) == 4

    def test_analysis_summary_stored(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        engine.analyze_game(game_in_db)

        summary = get_analysis_summary(db_conn, game_in_db)
        assert summary is not None
        assert summary["is_complete"] is True

    def test_stored_results_match_returned(
        self, db_conn, game_in_db, mock_stockfish
    ):
        engine = ReviewEngine(mock_stockfish, db_conn)
        result = engine.analyze_game(game_in_db)

        stored = get_analysis(db_conn, game_in_db)
        assert len(stored) == len(result.moves)

        for i, (returned_move, stored_move) in enumerate(
            zip(result.moves, stored)
        ):
            assert stored_move["move_index"] == i
            assert stored_move["move_san"] == returned_move.move_san
            assert stored_move["is_white"] == returned_move.is_white


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_nonexistent_game_raises(self, db_conn, mock_stockfish):
        engine = ReviewEngine(mock_stockfish, db_conn)
        with pytest.raises(ValueError, match="Game not found"):
            engine.analyze_game("nonexistent-game")

    def test_depth_enforces_minimum_20(self, db_conn, game_in_db, mock_stockfish):
        engine = ReviewEngine(mock_stockfish, db_conn, depth=10)
        # Internal depth should be clamped to 20
        assert engine._depth == 20

    def test_classification_summary_counts_correct(self, db_conn, game_in_db):
        mock_sf = MagicMock()

        # Gradually declining eval: White loses cp each move
        evals = iter(
            [
                _make_eval(chess.STARTING_FEN, cp=100, candidates=[
                    CandidateMove(move_san="e4", evaluation=100, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[0], cp=50, candidates=[
                    CandidateMove(move_san="e5", evaluation=50, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[1], cp=45, candidates=[
                    CandidateMove(move_san="Nf3", evaluation=45, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[2], cp=10, candidates=[
                    CandidateMove(move_san="d6", evaluation=10, mate_in=None)
                ]),
                _make_eval(SAMPLE_FENS[3], cp=5, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game(game_in_db)

        # White moves: e4 (loss=100-50=50 → inaccuracy), Nf3 (loss=45-10=35 → inaccuracy)
        assert result.white_summary.inaccuracy_count == 2

        # Black moves: e5 (loss=50-45=5 → excellent), d6 (loss=5-10→ clamped 0 → best)
        # Wait: for Black e5: before cp=50, after cp=45.
        # Black loss = cp_after - cp_before = 45 - 50 = -5, clamped to 0 → best
        # Black d6: before cp=10, after cp=5.
        # Black loss = cp_after - cp_before = 5 - 10 = -5, clamped to 0 → best
        assert result.black_summary.best_count == 2

    def test_custom_fen_starting_position(self, db_conn):
        """Games from a custom position use the FEN header as starting position."""
        custom_fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        game = ParsedGame(
            event="T", site="T", date="2024.01.01", round="-",
            white="w", black="b", result="*",
            additional_headers={"FEN": custom_fen},
            moves=["e5"],
            fens=["rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"],
        )
        insert_game(db_conn, "custom-fen-game", "user", "pgn", game)

        mock_sf = MagicMock()
        evals = iter(
            [
                _make_eval(custom_fen, cp=-20, candidates=[
                    CandidateMove(move_san="e5", evaluation=-20, mate_in=None)
                ]),
                _make_eval(game.fens[0], cp=-20, candidates=[]),
            ]
        )
        mock_sf.evaluate_position = MagicMock(side_effect=lambda *a, **kw: next(evals))

        engine = ReviewEngine(mock_sf, db_conn)
        result = engine.analyze_game("custom-fen-game")

        # The first evaluate_position call should use the custom FEN.
        first_call_fen = mock_sf.evaluate_position.call_args_list[0][0][0]
        assert first_call_fen == custom_fen
