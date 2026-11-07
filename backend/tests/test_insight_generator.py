"""Unit tests for the learning insight generator service."""

import pytest

from app.models import (
    AnalyzedMove,
    CandidateMove,
    LearningInsight,
    MoveClassification,
    PositionEvaluation,
)
from app.services.insight_generator import (
    generate_insight,
    generate_learning_summary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evaluation(fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1") -> PositionEvaluation:
    """Return a minimal PositionEvaluation for test scaffolding."""
    return PositionEvaluation(fen=fen, evaluation=0, mate_in=None, candidate_moves=[])


def _make_analyzed_move(
    move_number: int = 1,
    is_white: bool = True,
    move_san: str = "e4",
    classification: MoveClassification | None = MoveClassification.BEST,
    centipawn_loss: int | None = 0,
    candidate_moves: list[CandidateMove] | None = None,
    insight: LearningInsight | None = None,
) -> AnalyzedMove:
    """Return an AnalyzedMove with sensible defaults for testing."""
    return AnalyzedMove(
        move_number=move_number,
        is_white=is_white,
        move_san=move_san,
        position_before="startpos",
        position_after="startpos",
        evaluation_before=_make_evaluation(),
        evaluation_after=_make_evaluation(),
        classification=classification,
        centipawn_loss=centipawn_loss,
        candidate_moves=candidate_moves or [],
        insight=insight,
    )


# ---------------------------------------------------------------------------
# generate_insight tests
# ---------------------------------------------------------------------------

class TestGenerateInsight:
    """Tests for the generate_insight function."""

    def test_basic_blunder_insight(self) -> None:
        insight = generate_insight(
            move_number=5,
            is_white=True,
            played_move="Qh5",
            best_move="Nf3",
            centipawn_loss=250,
            classification=MoveClassification.BLUNDER,
            principal_variation=["Nf3", "Nc6", "Bb5"],
        )

        assert isinstance(insight, LearningInsight)
        assert insight.move_number == 5
        assert insight.is_white is True
        assert insight.played_move == "Qh5"
        assert insight.best_move == "Nf3"
        assert insight.centipawn_loss == 250
        assert insight.classification == MoveClassification.BLUNDER
        assert insight.principal_variation == ["Nf3", "Nc6", "Bb5"]

    def test_explanation_contains_key_info(self) -> None:
        insight = generate_insight(
            move_number=10,
            is_white=False,
            played_move="Bg4",
            best_move="d5",
            centipawn_loss=95,
            classification=MoveClassification.MISTAKE,
            principal_variation=["d5", "exd5", "Nxd5"],
        )

        assert "Black" in insight.explanation
        assert "Bg4" in insight.explanation
        assert "mistake" in insight.explanation
        assert "95" in insight.explanation
        assert "d5" in insight.explanation

    def test_white_move_explanation(self) -> None:
        insight = generate_insight(
            move_number=3,
            is_white=True,
            played_move="a3",
            best_move="Nf3",
            centipawn_loss=40,
            classification=MoveClassification.INACCURACY,
            principal_variation=["Nf3"],
        )

        assert "White" in insight.explanation
        assert "inaccuracy" in insight.explanation

    def test_pv_truncated_to_5_moves(self) -> None:
        long_pv = ["Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O"]
        insight = generate_insight(
            move_number=1,
            is_white=True,
            played_move="a4",
            best_move="Nf3",
            centipawn_loss=35,
            classification=MoveClassification.INACCURACY,
            principal_variation=long_pv,
        )

        assert len(insight.principal_variation) == 5
        assert insight.principal_variation == long_pv[:5]

    def test_pv_shorter_than_5_kept_as_is(self) -> None:
        short_pv = ["Nf3", "d5"]
        insight = generate_insight(
            move_number=1,
            is_white=True,
            played_move="a4",
            best_move="Nf3",
            centipawn_loss=35,
            classification=MoveClassification.INACCURACY,
            principal_variation=short_pv,
        )

        assert insight.principal_variation == short_pv

    def test_empty_pv(self) -> None:
        insight = generate_insight(
            move_number=1,
            is_white=True,
            played_move="a4",
            best_move="Nf3",
            centipawn_loss=35,
            classification=MoveClassification.INACCURACY,
            principal_variation=[],
        )

        assert insight.principal_variation == []
        assert "best continuation" not in insight.explanation

    def test_singular_centipawn_loss(self) -> None:
        """Centipawn loss of 1 should use singular 'centipawn'."""
        insight = generate_insight(
            move_number=1,
            is_white=True,
            played_move="a4",
            best_move="e4",
            centipawn_loss=1,
            classification=MoveClassification.INACCURACY,
            principal_variation=[],
        )

        # Should not have "centipawns" but "centipawn"
        assert "1 centipawn." in insight.explanation


# ---------------------------------------------------------------------------
# generate_learning_summary tests
# ---------------------------------------------------------------------------

class TestGenerateLearningSummary:
    """Tests for the generate_learning_summary function."""

    def test_empty_moves_returns_empty_summary(self) -> None:
        result = generate_learning_summary([])
        assert result == []

    def test_all_good_moves_returns_empty_summary(self) -> None:
        moves = [
            _make_analyzed_move(classification=MoveClassification.BEST, centipawn_loss=0),
            _make_analyzed_move(classification=MoveClassification.EXCELLENT, centipawn_loss=5),
            _make_analyzed_move(classification=MoveClassification.GOOD, centipawn_loss=20),
        ]
        result = generate_learning_summary(moves)
        assert result == []

    def test_collects_inaccuracies(self) -> None:
        moves = [
            _make_analyzed_move(
                move_number=1,
                classification=MoveClassification.BEST,
                centipawn_loss=0,
            ),
            _make_analyzed_move(
                move_number=2,
                is_white=False,
                move_san="a6",
                classification=MoveClassification.INACCURACY,
                centipawn_loss=50,
                candidate_moves=[CandidateMove("d5", 30, None)],
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 1
        assert result[0].move_number == 2
        assert result[0].classification == MoveClassification.INACCURACY

    def test_collects_mistakes_and_blunders(self) -> None:
        moves = [
            _make_analyzed_move(
                move_number=5,
                move_san="Bg4",
                classification=MoveClassification.MISTAKE,
                centipawn_loss=120,
                candidate_moves=[CandidateMove("Nf3", 10, None)],
            ),
            _make_analyzed_move(
                move_number=6,
                is_white=False,
                move_san="Qh4",
                classification=MoveClassification.BLUNDER,
                centipawn_loss=300,
                candidate_moves=[CandidateMove("d5", 0, None), CandidateMove("Nc6", -5, None)],
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 2
        assert result[0].classification == MoveClassification.MISTAKE
        assert result[1].classification == MoveClassification.BLUNDER

    def test_excludes_best_excellent_good(self) -> None:
        """Only inaccuracy, mistake, blunder should appear in summary."""
        moves = [
            _make_analyzed_move(classification=MoveClassification.BEST, centipawn_loss=0),
            _make_analyzed_move(classification=MoveClassification.EXCELLENT, centipawn_loss=8),
            _make_analyzed_move(classification=MoveClassification.GOOD, centipawn_loss=25),
            _make_analyzed_move(
                move_number=4,
                move_san="f6",
                classification=MoveClassification.BLUNDER,
                centipawn_loss=450,
                candidate_moves=[CandidateMove("Nf6", 0, None)],
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 1
        assert result[0].classification == MoveClassification.BLUNDER

    def test_skips_moves_without_classification(self) -> None:
        moves = [
            _make_analyzed_move(classification=None, centipawn_loss=None),
        ]
        result = generate_learning_summary(moves)
        assert result == []

    def test_skips_suboptimal_moves_without_centipawn_loss(self) -> None:
        moves = [
            _make_analyzed_move(
                classification=MoveClassification.MISTAKE,
                centipawn_loss=None,
            ),
        ]
        result = generate_learning_summary(moves)
        assert result == []

    def test_reuses_existing_insight_on_move(self) -> None:
        """If AnalyzedMove already has an insight, use it instead of generating a new one."""
        existing_insight = LearningInsight(
            move_number=3,
            is_white=True,
            played_move="Bxf7",
            best_move="Nf3",
            centipawn_loss=150,
            classification=MoveClassification.MISTAKE,
            principal_variation=["Nf3", "Nc6"],
            explanation="Pre-existing explanation.",
        )
        moves = [
            _make_analyzed_move(
                move_number=3,
                move_san="Bxf7",
                classification=MoveClassification.MISTAKE,
                centipawn_loss=150,
                insight=existing_insight,
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 1
        assert result[0] is existing_insight

    def test_preserves_game_order(self) -> None:
        moves = [
            _make_analyzed_move(
                move_number=2,
                move_san="a4",
                classification=MoveClassification.INACCURACY,
                centipawn_loss=40,
                candidate_moves=[CandidateMove("Nf3", 10, None)],
            ),
            _make_analyzed_move(
                move_number=5,
                move_san="Bxf7",
                classification=MoveClassification.BLUNDER,
                centipawn_loss=350,
                candidate_moves=[CandidateMove("Bc4", 0, None)],
            ),
            _make_analyzed_move(
                move_number=8,
                is_white=False,
                move_san="Qg5",
                classification=MoveClassification.MISTAKE,
                centipawn_loss=100,
                candidate_moves=[CandidateMove("Qd8", -10, None)],
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 3
        assert [i.move_number for i in result] == [2, 5, 8]

    def test_best_move_from_candidates(self) -> None:
        """When no existing insight, best_move should come from first candidate."""
        moves = [
            _make_analyzed_move(
                move_number=1,
                move_san="h4",
                classification=MoveClassification.INACCURACY,
                centipawn_loss=45,
                candidate_moves=[
                    CandidateMove("e4", 30, None),
                    CandidateMove("d4", 25, None),
                ],
            ),
        ]
        result = generate_learning_summary(moves)
        assert len(result) == 1
        assert result[0].best_move == "e4"
        assert result[0].principal_variation == ["e4", "d4"]
