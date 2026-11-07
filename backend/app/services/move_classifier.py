"""Move classification logic based on centipawn loss thresholds.

Classifies individual moves and aggregates classification counts per player.
"""

from app.models import AnalyzedMove, MoveClassification


def classify_move(centipawn_loss: int) -> MoveClassification:
    """Classify a move based on its centipawn loss.

    Thresholds:
        0        → BEST
        1–10     → EXCELLENT
        11–30    → GOOD
        31–80    → INACCURACY
        81–200   → MISTAKE
        201+     → BLUNDER

    Args:
        centipawn_loss: Non-negative integer centipawn loss value.

    Returns:
        The corresponding MoveClassification enum member.
    """
    if centipawn_loss == 0:
        return MoveClassification.BEST
    if centipawn_loss <= 10:
        return MoveClassification.EXCELLENT
    if centipawn_loss <= 30:
        return MoveClassification.GOOD
    if centipawn_loss <= 80:
        return MoveClassification.INACCURACY
    if centipawn_loss <= 200:
        return MoveClassification.MISTAKE
    return MoveClassification.BLUNDER


def classify_move_safe(centipawn_loss: int | None) -> MoveClassification | None:
    """Classify a move, returning None when centipawn loss is unavailable.

    Args:
        centipawn_loss: Centipawn loss value, or None if unavailable.

    Returns:
        The MoveClassification, or None if centipawn_loss is None.
    """
    if centipawn_loss is None:
        return None
    return classify_move(centipawn_loss)


def compute_classification_summary(
    moves: list[AnalyzedMove], is_white: bool
) -> dict[str, int]:
    """Aggregate classification counts for a single player.

    Filters the move list to only the specified player's moves and counts
    occurrences of each MoveClassification category.

    Args:
        moves: List of analyzed moves from the game.
        is_white: True to count White's moves, False for Black's.

    Returns:
        A dict mapping each classification value string to its count, e.g.
        {"best": 5, "excellent": 3, "good": 10, "inaccuracy": 2,
         "mistake": 1, "blunder": 0}.
    """
    counts: dict[str, int] = {cls.value: 0 for cls in MoveClassification}

    for move in moves:
        if move.is_white != is_white:
            continue
        if move.classification is not None:
            counts[move.classification.value] += 1

    return counts
