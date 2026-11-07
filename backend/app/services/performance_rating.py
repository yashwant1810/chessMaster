"""Performance rating computation based on centipawn losses.

Estimates an ELO-like rating from cumulative move accuracy.  Each
centipawn loss is converted to an accuracy fraction via an exponential
decay function, and the running mean accuracy is mapped linearly onto
the [0, 3000] rating scale.

* Perfect play (0 cp loss every move) → 3000
* Very poor play (high cp losses)     → approaches 0
"""

from __future__ import annotations

import math

# Scaling constant for the exponential accuracy decay.
# A centipawn loss of ~150 yields roughly 50 % accuracy.
_ACCURACY_DECAY_K = 200.0

# Rating bounds.
_MIN_RATING = 0
_MAX_RATING = 3000


def _centipawn_loss_to_accuracy(cp_loss: int) -> float:
    """Convert a single centipawn loss to an accuracy fraction in [0, 1].

    Uses an exponential decay: accuracy = e^(-cp_loss / k).
    A centipawn loss of 0 gives 1.0 (perfect); large losses approach 0.
    """
    return math.exp(-cp_loss / _ACCURACY_DECAY_K)


def _accuracy_to_rating(accuracy: float) -> int:
    """Map an accuracy fraction in [0, 1] to a rating in [0, 3000].

    The mapping is linear: rating = accuracy * 3000, clamped to bounds.
    """
    raw = accuracy * _MAX_RATING
    return max(_MIN_RATING, min(_MAX_RATING, round(raw)))


def compute_performance_rating(centipawn_losses: list[int]) -> int:
    """Compute a cumulative performance rating from centipawn losses.

    Args:
        centipawn_losses: Non-negative centipawn loss for each evaluated
            move by the player.

    Returns:
        A whole-number rating in [0, 3000].  An empty list returns 0.
    """
    if not centipawn_losses:
        return _MIN_RATING

    total_accuracy = 0.0
    for cp_loss in centipawn_losses:
        total_accuracy += _centipawn_loss_to_accuracy(cp_loss)

    mean_accuracy = total_accuracy / len(centipawn_losses)
    return _accuracy_to_rating(mean_accuracy)


def compute_cumulative_ratings(centipawn_losses: list[int]) -> list[int]:
    """Compute the running performance rating after each move.

    Args:
        centipawn_losses: Non-negative centipawn loss for each evaluated
            move by the player.

    Returns:
        A list of the same length as *centipawn_losses* where the i-th
        element is the cumulative rating computed from the first (i + 1)
        centipawn losses.  Every value is a whole integer in [0, 3000].
        An empty input returns an empty list.
    """
    ratings: list[int] = []
    total_accuracy = 0.0

    for idx, cp_loss in enumerate(centipawn_losses, start=1):
        total_accuracy += _centipawn_loss_to_accuracy(cp_loss)
        mean_accuracy = total_accuracy / idx
        ratings.append(_accuracy_to_rating(mean_accuracy))

    return ratings
