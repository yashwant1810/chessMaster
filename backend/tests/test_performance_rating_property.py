"""Property-based tests for performance rating range invariant.

Feature: chess-review-engine, Property 10: Performance rating range invariant

**Validates: Requirements 8.1**
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.performance_rating import (
    compute_cumulative_ratings,
    compute_performance_rating,
)


# Strategy: non-empty lists of non-negative centipawn losses in [0, 500].
cp_loss_lists = st.lists(
    st.integers(min_value=0, max_value=500),
    min_size=1,
    max_size=200,
)


class TestPerformanceRatingRangeProperty:
    """Property 10: Performance Rating Range Invariant.

    For any non-empty sequence of non-negative centipawn loss values,
    every cumulative rating SHALL be a whole integer in [0, 3000].
    """

    @given(losses=cp_loss_lists)
    @settings(max_examples=200)
    def test_cumulative_ratings_are_integers_in_range(
        self, losses: list[int]
    ) -> None:
        """Every cumulative rating is an int in [0, 3000].

        **Validates: Requirements 8.1**
        """
        ratings = compute_cumulative_ratings(losses)

        # Length must match input length.
        assert len(ratings) == len(losses)

        for rating in ratings:
            assert isinstance(rating, int), (
                f"Expected int, got {type(rating)}"
            )
            assert 0 <= rating <= 3000, (
                f"Rating {rating} outside [0, 3000]"
            )

    @given(losses=cp_loss_lists)
    @settings(max_examples=200)
    def test_final_rating_is_integer_in_range(
        self, losses: list[int]
    ) -> None:
        """compute_performance_rating returns an int in [0, 3000].

        **Validates: Requirements 8.1**
        """
        rating = compute_performance_rating(losses)

        assert isinstance(rating, int), (
            f"Expected int, got {type(rating)}"
        )
        assert 0 <= rating <= 3000, (
            f"Rating {rating} outside [0, 3000]"
        )

    @given(losses=cp_loss_lists)
    @settings(max_examples=200)
    def test_final_cumulative_matches_overall(
        self, losses: list[int]
    ) -> None:
        """Last cumulative rating equals the full compute_performance_rating.

        **Validates: Requirements 8.1**
        """
        ratings = compute_cumulative_ratings(losses)
        overall = compute_performance_rating(losses)

        assert ratings[-1] == overall
