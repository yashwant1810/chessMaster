"""Unit tests for the performance rating computation module."""

import math

import pytest

from app.services.performance_rating import (
    compute_cumulative_ratings,
    compute_performance_rating,
)


class TestComputePerformanceRating:
    """Tests for compute_performance_rating."""

    def test_empty_list_returns_zero(self) -> None:
        assert compute_performance_rating([]) == 0

    def test_perfect_play_returns_3000(self) -> None:
        """All moves with 0 cp loss → maximum rating."""
        assert compute_performance_rating([0, 0, 0, 0, 0]) == 3000

    def test_single_perfect_move(self) -> None:
        assert compute_performance_rating([0]) == 3000

    def test_very_high_losses_approach_zero(self) -> None:
        """Extremely large losses should yield a rating near 0."""
        rating = compute_performance_rating([5000, 5000, 5000])
        assert rating <= 50  # close to 0

    def test_moderate_losses_give_mid_range(self) -> None:
        """Moderate cp losses should produce a mid-range rating."""
        rating = compute_performance_rating([50, 50, 50, 50])
        assert 500 < rating < 2800

    def test_result_is_integer(self) -> None:
        rating = compute_performance_rating([10, 20, 30])
        assert isinstance(rating, int)

    def test_result_clamped_to_bounds(self) -> None:
        rating = compute_performance_rating([0])
        assert 0 <= rating <= 3000

        rating_low = compute_performance_rating([10000])
        assert 0 <= rating_low <= 3000

    def test_higher_losses_give_lower_rating(self) -> None:
        """More centipawn loss → lower rating."""
        rating_good = compute_performance_rating([5, 5, 5])
        rating_bad = compute_performance_rating([200, 200, 200])
        assert rating_good > rating_bad

    def test_mixed_losses(self) -> None:
        """A mix of good and bad moves gives an intermediate rating."""
        rating = compute_performance_rating([0, 0, 300, 0, 0])
        assert 0 < rating < 3000


class TestComputeCumulativeRatings:
    """Tests for compute_cumulative_ratings."""

    def test_empty_list_returns_empty(self) -> None:
        assert compute_cumulative_ratings([]) == []

    def test_length_matches_input(self) -> None:
        losses = [10, 20, 30, 40, 50]
        ratings = compute_cumulative_ratings(losses)
        assert len(ratings) == len(losses)

    def test_single_perfect_move(self) -> None:
        ratings = compute_cumulative_ratings([0])
        assert ratings == [3000]

    def test_all_perfect_moves(self) -> None:
        ratings = compute_cumulative_ratings([0, 0, 0])
        assert ratings == [3000, 3000, 3000]

    def test_all_values_are_integers(self) -> None:
        ratings = compute_cumulative_ratings([15, 45, 100, 200])
        assert all(isinstance(r, int) for r in ratings)

    def test_all_values_in_range(self) -> None:
        ratings = compute_cumulative_ratings([0, 50, 500, 5000])
        assert all(0 <= r <= 3000 for r in ratings)

    def test_last_element_equals_full_rating(self) -> None:
        """The last cumulative rating should match the overall rating."""
        losses = [10, 50, 100, 20]
        ratings = compute_cumulative_ratings(losses)
        full_rating = compute_performance_rating(losses)
        assert ratings[-1] == full_rating

    def test_rating_decreases_with_bad_move(self) -> None:
        """Adding a very bad move should lower the cumulative rating."""
        ratings = compute_cumulative_ratings([0, 0, 0, 500])
        # First three should be 3000, fourth should drop
        assert ratings[0] == 3000
        assert ratings[3] < ratings[2]

    def test_rating_increases_with_good_moves_after_bad(self) -> None:
        """Good moves after a bad move should recover the rating somewhat."""
        ratings = compute_cumulative_ratings([500, 0, 0, 0, 0])
        # Rating should increase as good moves accumulate
        assert ratings[-1] > ratings[0]
