"""Property-based tests for move classification threshold correctness.

Feature: chess-review-engine, Property 3: Move classification threshold correctness

**Validates: Requirements 6.1, 6.2**
"""

from hypothesis import given, settings, strategies as st

from app.models import MoveClassification
from app.services.move_classifier import classify_move

# Defined thresholds from the spec:
#   0        → BEST
#   1–10     → EXCELLENT
#   11–30    → GOOD
#   31–80    → INACCURACY
#   81–200   → MISTAKE
#   201+     → BLUNDER

_THRESHOLDS: list[tuple[int, int, MoveClassification]] = [
    (0, 0, MoveClassification.BEST),
    (1, 10, MoveClassification.EXCELLENT),
    (11, 30, MoveClassification.GOOD),
    (31, 80, MoveClassification.INACCURACY),
    (81, 200, MoveClassification.MISTAKE),
    (201, 10_000, MoveClassification.BLUNDER),
]


def _expected_classification(centipawn_loss: int) -> MoveClassification:
    """Return the single expected classification for a centipawn loss value."""
    for low, high, classification in _THRESHOLDS:
        if low <= centipawn_loss <= high:
            return classification
    # Any value above the last explicit upper bound is still a blunder.
    return MoveClassification.BLUNDER


class TestMoveClassificationThresholdCorrectness:
    """Property 3 – Move Classification Threshold Correctness.

    For any non-negative integer centipawn loss value, classify_move SHALL
    assign exactly one classification that matches the defined thresholds.
    """

    @given(centipawn_loss=st.integers(min_value=0, max_value=50_000))
    @settings(max_examples=200)
    def test_classification_matches_defined_thresholds(
        self, centipawn_loss: int
    ) -> None:
        """**Validates: Requirements 6.1, 6.2**

        Every non-negative centipawn loss maps to the correct classification.
        """
        result = classify_move(centipawn_loss)
        expected = _expected_classification(centipawn_loss)
        assert result == expected, (
            f"centipawn_loss={centipawn_loss}: "
            f"got {result!r}, expected {expected!r}"
        )

    @given(centipawn_loss=st.integers(min_value=0, max_value=50_000))
    @settings(max_examples=200)
    def test_exactly_one_classification_per_value(
        self, centipawn_loss: int
    ) -> None:
        """**Validates: Requirements 6.1, 6.2**

        Each centipawn loss value matches exactly one classification category.
        """
        result = classify_move(centipawn_loss)

        # The result must be a valid MoveClassification member.
        assert isinstance(result, MoveClassification)

        # Exactly one threshold range contains this value.
        matching = [
            cls
            for low, high, cls in _THRESHOLDS
            if low <= centipawn_loss <= high
        ]
        # Values above the explicit upper bound still match BLUNDER.
        if not matching:
            matching = [MoveClassification.BLUNDER]

        assert len(matching) == 1, (
            f"centipawn_loss={centipawn_loss} matched {len(matching)} ranges"
        )
        assert result == matching[0]
