"""Unit tests for move classification logic."""

from app.models import (
    AnalyzedMove,
    CandidateMove,
    MoveClassification,
    PositionEvaluation,
)
from app.services.move_classifier import (
    classify_move,
    classify_move_safe,
    compute_classification_summary,
)


# ---------------------------------------------------------------------------
# Helper to build a minimal AnalyzedMove for summary tests
# ---------------------------------------------------------------------------

_DUMMY_EVAL = PositionEvaluation(
    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    evaluation=0,
    mate_in=None,
    candidate_moves=[],
)


def _make_move(
    *,
    is_white: bool,
    classification: MoveClassification | None,
    move_number: int = 1,
) -> AnalyzedMove:
    return AnalyzedMove(
        move_number=move_number,
        is_white=is_white,
        move_san="e4",
        position_before="startpos",
        position_after="startpos",
        evaluation_before=_DUMMY_EVAL,
        evaluation_after=_DUMMY_EVAL,
        classification=classification,
        centipawn_loss=0,
        candidate_moves=[],
        insight=None,
    )


# ---------------------------------------------------------------------------
# classify_move – threshold boundaries
# ---------------------------------------------------------------------------


class TestClassifyMove:
    """Tests for classify_move covering every threshold boundary."""

    def test_zero_is_best(self) -> None:
        assert classify_move(0) == MoveClassification.BEST

    def test_one_is_excellent(self) -> None:
        assert classify_move(1) == MoveClassification.EXCELLENT

    def test_ten_is_excellent(self) -> None:
        assert classify_move(10) == MoveClassification.EXCELLENT

    def test_eleven_is_good(self) -> None:
        assert classify_move(11) == MoveClassification.GOOD

    def test_thirty_is_good(self) -> None:
        assert classify_move(30) == MoveClassification.GOOD

    def test_thirtyone_is_inaccuracy(self) -> None:
        assert classify_move(31) == MoveClassification.INACCURACY

    def test_eighty_is_inaccuracy(self) -> None:
        assert classify_move(80) == MoveClassification.INACCURACY

    def test_eightyone_is_mistake(self) -> None:
        assert classify_move(81) == MoveClassification.MISTAKE

    def test_twohundred_is_mistake(self) -> None:
        assert classify_move(200) == MoveClassification.MISTAKE

    def test_twohundredone_is_blunder(self) -> None:
        assert classify_move(201) == MoveClassification.BLUNDER

    def test_large_value_is_blunder(self) -> None:
        assert classify_move(9999) == MoveClassification.BLUNDER

    def test_mid_excellent_range(self) -> None:
        assert classify_move(5) == MoveClassification.EXCELLENT

    def test_mid_good_range(self) -> None:
        assert classify_move(20) == MoveClassification.GOOD

    def test_mid_inaccuracy_range(self) -> None:
        assert classify_move(55) == MoveClassification.INACCURACY

    def test_mid_mistake_range(self) -> None:
        assert classify_move(140) == MoveClassification.MISTAKE


# ---------------------------------------------------------------------------
# classify_move_safe – None handling
# ---------------------------------------------------------------------------


class TestClassifyMoveSafe:
    """Tests for classify_move_safe with None input."""

    def test_none_returns_none(self) -> None:
        assert classify_move_safe(None) is None

    def test_zero_returns_best(self) -> None:
        assert classify_move_safe(0) == MoveClassification.BEST

    def test_positive_value_delegates(self) -> None:
        assert classify_move_safe(50) == MoveClassification.INACCURACY


# ---------------------------------------------------------------------------
# compute_classification_summary
# ---------------------------------------------------------------------------


class TestComputeClassificationSummary:
    """Tests for compute_classification_summary."""

    def test_empty_move_list(self) -> None:
        result = compute_classification_summary([], is_white=True)
        assert result == {
            "best": 0,
            "excellent": 0,
            "good": 0,
            "inaccuracy": 0,
            "mistake": 0,
            "blunder": 0,
        }

    def test_counts_only_white_moves(self) -> None:
        moves = [
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=False, classification=MoveClassification.BLUNDER),
            _make_move(is_white=True, classification=MoveClassification.BEST),
        ]
        result = compute_classification_summary(moves, is_white=True)
        assert result["best"] == 2
        assert result["blunder"] == 0

    def test_counts_only_black_moves(self) -> None:
        moves = [
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=False, classification=MoveClassification.MISTAKE),
            _make_move(is_white=False, classification=MoveClassification.MISTAKE),
        ]
        result = compute_classification_summary(moves, is_white=False)
        assert result["mistake"] == 2
        assert result["best"] == 0

    def test_all_categories_counted(self) -> None:
        moves = [
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=True, classification=MoveClassification.EXCELLENT),
            _make_move(is_white=True, classification=MoveClassification.GOOD),
            _make_move(is_white=True, classification=MoveClassification.INACCURACY),
            _make_move(is_white=True, classification=MoveClassification.MISTAKE),
            _make_move(is_white=True, classification=MoveClassification.BLUNDER),
        ]
        result = compute_classification_summary(moves, is_white=True)
        assert result == {
            "best": 1,
            "excellent": 1,
            "good": 1,
            "inaccuracy": 1,
            "mistake": 1,
            "blunder": 1,
        }

    def test_none_classification_skipped(self) -> None:
        moves = [
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=True, classification=None),
            _make_move(is_white=True, classification=MoveClassification.GOOD),
        ]
        result = compute_classification_summary(moves, is_white=True)
        assert result["best"] == 1
        assert result["good"] == 1
        # Total classified should be 2, not 3
        assert sum(result.values()) == 2

    def test_mixed_players_and_classifications(self) -> None:
        moves = [
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=False, classification=MoveClassification.INACCURACY),
            _make_move(is_white=True, classification=MoveClassification.EXCELLENT),
            _make_move(is_white=False, classification=MoveClassification.BLUNDER),
            _make_move(is_white=True, classification=MoveClassification.BEST),
            _make_move(is_white=False, classification=MoveClassification.GOOD),
        ]
        white_result = compute_classification_summary(moves, is_white=True)
        assert white_result["best"] == 2
        assert white_result["excellent"] == 1
        assert sum(white_result.values()) == 3

        black_result = compute_classification_summary(moves, is_white=False)
        assert black_result["inaccuracy"] == 1
        assert black_result["blunder"] == 1
        assert black_result["good"] == 1
        assert sum(black_result.values()) == 3
