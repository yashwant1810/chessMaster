"""Property-based tests for learning insight completeness.

Feature: chess-review-engine, Property 11: Learning insight completeness

**Validates: Requirements 9.1, 9.2**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import LearningInsight, MoveClassification
from app.services.insight_generator import generate_insight

# Only suboptimal classifications warrant learning insights.
_SUBOPTIMAL_CLASSIFICATIONS = st.sampled_from([
    MoveClassification.INACCURACY,
    MoveClassification.MISTAKE,
    MoveClassification.BLUNDER,
])

# Pieces and files/ranks for generating plausible SAN move strings.
_PIECES = ["N", "B", "R", "Q", "K"]
_FILES = list("abcdefgh")
_RANKS = list("12345678")


@st.composite
def san_moves(draw: st.DrawFn) -> str:
    """Generate plausible SAN-format chess move strings.

    Produces moves like 'e4', 'Nf3', 'Bxe5', 'O-O', 'O-O-O', etc.
    These are syntactically plausible SAN strings, not necessarily legal
    in any given position, but sufficient for testing insight generation.
    """
    kind = draw(st.integers(min_value=0, max_value=3))
    if kind == 0:
        # Pawn move: e4, d5, etc.
        f = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        return f"{f}{r}"
    elif kind == 1:
        # Piece move: Nf3, Bb5, Qd1, etc.
        piece = draw(st.sampled_from(_PIECES))
        f = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        capture = draw(st.sampled_from(["", "x"]))
        return f"{piece}{capture}{f}{r}"
    elif kind == 2:
        # Castling
        return draw(st.sampled_from(["O-O", "O-O-O"]))
    else:
        # Pawn capture: exd5, fxg6, etc.
        f1 = draw(st.sampled_from(_FILES))
        f2 = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        return f"{f1}x{f2}{r}"


@st.composite
def principal_variations(draw: st.DrawFn) -> list[str]:
    """Generate a principal variation line of 0–10 moves.

    The PV can be longer than the max allowed (5) so that the truncation
    behaviour of generate_insight is exercised.
    """
    length = draw(st.integers(min_value=0, max_value=10))
    return [draw(san_moves()) for _ in range(length)]


@settings(max_examples=100)
@given(
    move_number=st.integers(min_value=1, max_value=200),
    is_white=st.booleans(),
    played_move=san_moves(),
    best_move=san_moves(),
    centipawn_loss=st.integers(min_value=31, max_value=1000),
    classification=_SUBOPTIMAL_CLASSIFICATIONS,
    principal_variation=principal_variations(),
)
def test_insight_contains_centipawn_loss(
    move_number: int,
    is_white: bool,
    played_move: str,
    best_move: str,
    centipawn_loss: int,
    classification: MoveClassification,
    principal_variation: list[str],
) -> None:
    """The insight centipawn loss equals the input centipawn loss.

    **Validates: Requirements 9.1**
    """
    insight = generate_insight(
        move_number=move_number,
        is_white=is_white,
        played_move=played_move,
        best_move=best_move,
        centipawn_loss=centipawn_loss,
        classification=classification,
        principal_variation=principal_variation,
    )

    assert isinstance(insight, LearningInsight)
    assert insight.centipawn_loss == centipawn_loss


@settings(max_examples=100)
@given(
    move_number=st.integers(min_value=1, max_value=200),
    is_white=st.booleans(),
    played_move=san_moves(),
    best_move=san_moves(),
    centipawn_loss=st.integers(min_value=31, max_value=1000),
    classification=_SUBOPTIMAL_CLASSIFICATIONS,
    principal_variation=principal_variations(),
)
def test_insight_contains_best_move_in_san(
    move_number: int,
    is_white: bool,
    played_move: str,
    best_move: str,
    centipawn_loss: int,
    classification: MoveClassification,
    principal_variation: list[str],
) -> None:
    """The insight best move matches the input best move in SAN notation.

    **Validates: Requirements 9.1**
    """
    insight = generate_insight(
        move_number=move_number,
        is_white=is_white,
        played_move=played_move,
        best_move=best_move,
        centipawn_loss=centipawn_loss,
        classification=classification,
        principal_variation=principal_variation,
    )

    assert isinstance(insight, LearningInsight)
    assert insight.best_move == best_move
    assert len(insight.best_move) > 0


@settings(max_examples=100)
@given(
    move_number=st.integers(min_value=1, max_value=200),
    is_white=st.booleans(),
    played_move=san_moves(),
    best_move=san_moves(),
    centipawn_loss=st.integers(min_value=31, max_value=1000),
    classification=_SUBOPTIMAL_CLASSIFICATIONS,
    principal_variation=principal_variations(),
)
def test_insight_pv_at_most_5_moves(
    move_number: int,
    is_white: bool,
    played_move: str,
    best_move: str,
    centipawn_loss: int,
    classification: MoveClassification,
    principal_variation: list[str],
) -> None:
    """The principal variation in the insight has at most 5 moves.

    **Validates: Requirements 9.2**
    """
    insight = generate_insight(
        move_number=move_number,
        is_white=is_white,
        played_move=played_move,
        best_move=best_move,
        centipawn_loss=centipawn_loss,
        classification=classification,
        principal_variation=principal_variation,
    )

    assert isinstance(insight, LearningInsight)
    assert len(insight.principal_variation) <= 5
    # When the input PV is short enough, all moves are preserved.
    expected_pv = principal_variation[:5]
    assert insight.principal_variation == expected_pv
