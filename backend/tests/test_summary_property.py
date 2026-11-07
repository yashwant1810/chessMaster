"""Property-based tests for classification summary aggregation.

Feature: chess-review-engine, Property 4: Classification summary aggregation

**Validates: Requirements 6.4**
"""

from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import (
    AnalyzedMove,
    MoveClassification,
    PositionEvaluation,
)
from app.services.move_classifier import compute_classification_summary


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_DUMMY_EVAL = PositionEvaluation(
    fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    evaluation=0,
    mate_in=None,
    candidate_moves=[],
)

_CLASSIFICATIONS = st.sampled_from(list(MoveClassification))
_OPTIONAL_CLASSIFICATIONS = st.one_of(st.none(), _CLASSIFICATIONS)


@st.composite
def analyzed_move(draw: st.DrawFn) -> AnalyzedMove:
    """Generate a random AnalyzedMove with a random player and classification."""
    return AnalyzedMove(
        move_number=draw(st.integers(min_value=1, max_value=200)),
        is_white=draw(st.booleans()),
        move_san="e4",
        position_before="startpos",
        position_after="startpos",
        evaluation_before=_DUMMY_EVAL,
        evaluation_after=_DUMMY_EVAL,
        classification=draw(_OPTIONAL_CLASSIFICATIONS),
        centipawn_loss=draw(st.integers(min_value=0, max_value=500)),
        candidate_moves=[],
        insight=None,
    )


analyzed_move_lists = st.lists(analyzed_move(), min_size=0, max_size=80)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestClassificationSummaryAggregation:
    """Property 4: Classification Summary Aggregation."""

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_white_counts_match_actual_occurrences(
        self, moves: list[AnalyzedMove]
    ) -> None:
        """Per-player classification counts for White equal actual occurrences.

        **Validates: Requirements 6.4**
        """
        summary = compute_classification_summary(moves, is_white=True)

        # Manually count White's classified moves
        white_moves = [m for m in moves if m.is_white and m.classification is not None]
        expected = Counter(m.classification.value for m in white_moves)

        for cls in MoveClassification:
            assert summary[cls.value] == expected.get(cls.value, 0)

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_black_counts_match_actual_occurrences(
        self, moves: list[AnalyzedMove]
    ) -> None:
        """Per-player classification counts for Black equal actual occurrences.

        **Validates: Requirements 6.4**
        """
        summary = compute_classification_summary(moves, is_white=False)

        # Manually count Black's classified moves
        black_moves = [
            m for m in moves if not m.is_white and m.classification is not None
        ]
        expected = Counter(m.classification.value for m in black_moves)

        for cls in MoveClassification:
            assert summary[cls.value] == expected.get(cls.value, 0)

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_keys_cover_all_classifications(
        self, moves: list[AnalyzedMove]
    ) -> None:
        """Summary dict always contains a key for every MoveClassification value.

        **Validates: Requirements 6.4**
        """
        for is_white in (True, False):
            summary = compute_classification_summary(moves, is_white=is_white)
            for cls in MoveClassification:
                assert cls.value in summary

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_total_classified_equals_sum_of_counts(
        self, moves: list[AnalyzedMove]
    ) -> None:
        """Sum of all classification counts equals the number of classified moves for that player.

        **Validates: Requirements 6.4**
        """
        for is_white in (True, False):
            summary = compute_classification_summary(moves, is_white=is_white)
            expected_total = sum(
                1
                for m in moves
                if m.is_white == is_white and m.classification is not None
            )
            assert sum(summary.values()) == expected_total

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_counts_are_non_negative(self, moves: list[AnalyzedMove]) -> None:
        """All classification counts are non-negative integers.

        **Validates: Requirements 6.4**
        """
        for is_white in (True, False):
            summary = compute_classification_summary(moves, is_white=is_white)
            for count in summary.values():
                assert isinstance(count, int)
                assert count >= 0
