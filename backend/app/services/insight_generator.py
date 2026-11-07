"""Learning insight generation for suboptimal chess moves.

Generates textual explanations for moves classified as inaccuracy, mistake,
or blunder, including centipawn loss, suggested best move, and principal
variation lines.

Requirements: 9.1, 9.2, 9.4
"""

from app.models import AnalyzedMove, LearningInsight, MoveClassification

# Classifications that are considered suboptimal and warrant learning insights.
_SUBOPTIMAL_CLASSIFICATIONS = frozenset({
    MoveClassification.INACCURACY,
    MoveClassification.MISTAKE,
    MoveClassification.BLUNDER,
})

# Maximum number of moves in the principal variation line.
_MAX_PV_LENGTH = 5


def _build_explanation(
    is_white: bool,
    played_move: str,
    best_move: str,
    centipawn_loss: int,
    classification: MoveClassification,
    principal_variation: list[str],
) -> str:
    """Build a human-readable explanation for a suboptimal move.

    The explanation describes why the move was suboptimal, referencing the
    centipawn loss and what the best continuation was.
    """
    color = "White" if is_white else "Black"
    class_label = classification.value

    pv_display = ""
    if principal_variation:
        pv_display = f" The best continuation was {', '.join(principal_variation)}."

    return (
        f"{color} played {played_move}, which is a {class_label} "
        f"losing {centipawn_loss} centipawn{'s' if centipawn_loss != 1 else ''}. "
        f"The best move was {best_move}.{pv_display}"
    )


def generate_insight(
    move_number: int,
    is_white: bool,
    played_move: str,
    best_move: str,
    centipawn_loss: int,
    classification: MoveClassification,
    principal_variation: list[str],
) -> LearningInsight:
    """Generate a learning insight for a suboptimal move.

    Creates a LearningInsight with the centipawn loss, suggested best move
    in SAN notation, a principal variation line of up to 5 moves, and a
    textual explanation describing why the move was suboptimal.

    Args:
        move_number: The full move number (1-based).
        is_white: True if the move was played by White.
        played_move: The move actually played, in SAN notation.
        best_move: The best move identified by Stockfish, in SAN notation.
        centipawn_loss: The centipawn loss between the played move and the best move.
        classification: The move classification (should be inaccuracy, mistake, or blunder).
        principal_variation: The principal variation line from Stockfish.

    Returns:
        A LearningInsight dataclass with all fields populated.
    """
    # Truncate principal variation to at most 5 moves.
    truncated_pv = principal_variation[:_MAX_PV_LENGTH]

    explanation = _build_explanation(
        is_white=is_white,
        played_move=played_move,
        best_move=best_move,
        centipawn_loss=centipawn_loss,
        classification=classification,
        principal_variation=truncated_pv,
    )

    return LearningInsight(
        move_number=move_number,
        is_white=is_white,
        played_move=played_move,
        best_move=best_move,
        centipawn_loss=centipawn_loss,
        classification=classification,
        principal_variation=truncated_pv,
        explanation=explanation,
    )


def generate_learning_summary(moves: list[AnalyzedMove]) -> list[LearningInsight]:
    """Collect learning insights for all suboptimal moves in a game.

    Iterates through the analyzed moves and generates insights for every
    move classified as inaccuracy, mistake, or blunder. Moves classified
    as best, excellent, or good are excluded.

    Args:
        moves: The list of analyzed moves from a completed game analysis.

    Returns:
        A list of LearningInsight objects, one per suboptimal move, in
        the order they appeared in the game.

    Requirements: 9.4
    """
    insights: list[LearningInsight] = []

    for move in moves:
        # Skip moves without a classification or that are not suboptimal.
        if move.classification is None:
            continue
        if move.classification not in _SUBOPTIMAL_CLASSIFICATIONS:
            continue
        # Skip moves missing centipawn loss data (cannot generate insight).
        if move.centipawn_loss is None:
            continue

        # If the move already has an insight attached, reuse it.
        if move.insight is not None:
            insights.append(move.insight)
            continue

        # Determine the best move from the candidate moves list.
        best_move = ""
        principal_variation: list[str] = []
        if move.candidate_moves:
            best_move = move.candidate_moves[0].move_san
            # The principal variation is the sequence of best candidate moves.
            principal_variation = [c.move_san for c in move.candidate_moves]

        insight = generate_insight(
            move_number=move.move_number,
            is_white=move.is_white,
            played_move=move.move_san,
            best_move=best_move,
            centipawn_loss=move.centipawn_loss,
            classification=move.classification,
            principal_variation=principal_variation,
        )
        insights.append(insight)

    return insights
