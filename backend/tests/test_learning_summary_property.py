"""Property-based tests for learning summary completeness.

Feature: chess-review-engine, Property 12: Learning summary includes all suboptimal moves

**Validates: Requirements 9.4**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models import (
    AnalyzedMove,
    CandidateMove,
    LearningInsight,
    MoveClassification,
    PositionEvaluation,
)
from app.services.insight_generator import generate_learning_summary

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SUBOPTIMAL = frozenset({
    MoveClassification.INACCURACY,
    MoveClassification.MISTAKE,
    MoveClassification.BLUNDER,
})

_OPTIMAL = frozenset({
    MoveClassification.BEST,
    MoveClassification.EXCELLENT,
    MoveClassification.GOOD,
})

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_DUMMY_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_DUMMY_EVAL = PositionEvaluation(
    fen=_DUMMY_FEN,
    evaluation=0,
    mate_in=None,
    candidate_moves=[],
)

_ALL_CLASSIFICATIONS = st.sampled_from(list(MoveClassification))
_OPTIONAL_CLASSIFICATIONS = st.one_of(st.none(), _ALL_CLASSIFICATIONS)

_PIECES = ["N", "B", "R", "Q", "K"]
_FILES = list("abcdefgh")
_RANKS = list("12345678")


@st.composite
def san_moves(draw: st.DrawFn) -> str:
    """Generate plausible SAN-format chess move strings."""
    kind = draw(st.integers(min_value=0, max_value=3))
    if kind == 0:
        f = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        return f"{f}{r}"
    elif kind == 1:
        piece = draw(st.sampled_from(_PIECES))
        f = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        capture = draw(st.sampled_from(["", "x"]))
        return f"{piece}{capture}{f}{r}"
    elif kind == 2:
        return draw(st.sampled_from(["O-O", "O-O-O"]))
    else:
        f1 = draw(st.sampled_from(_FILES))
        f2 = draw(st.sampled_from(_FILES))
        r = draw(st.sampled_from(_RANKS))
        return f"{f1}x{f2}{r}"


@st.composite
def candidate_move_lists(draw: st.DrawFn) -> list[CandidateMove]:
    """Generate a list of 0–3 candidate moves."""
    length = draw(st.integers(min_value=0, max_value=3))
    return [
        CandidateMove(
            move_san=draw(san_moves()),
            evaluation=draw(st.integers(min_value=-500, max_value=500)),
            mate_in=None,
        )
        for _ in range(length)
    ]


@st.composite
def analyzed_move(draw: st.DrawFn) -> AnalyzedMove:
    """Generate a random AnalyzedMove with mixed classifications.

    Suboptimal moves always have a non-None centipawn_loss so that the
    summary generator can create insights for them.
    """
    classification = draw(_OPTIONAL_CLASSIFICATIONS)
    is_white = draw(st.booleans())
    move_san = draw(san_moves())
    candidates = draw(candidate_move_lists())

    # Suboptimal moves need a valid centipawn_loss for insight generation.
    if classification in _SUBOPTIMAL:
        centipawn_loss: int | None = draw(st.integers(min_value=31, max_value=1000))
    else:
        centipawn_loss = draw(st.one_of(
            st.none(),
            st.integers(min_value=0, max_value=500),
        ))

    return AnalyzedMove(
        move_number=draw(st.integers(min_value=1, max_value=200)),
        is_white=is_white,
        move_san=move_san,
        position_before=_DUMMY_FEN,
        position_after=_DUMMY_FEN,
        evaluation_before=_DUMMY_EVAL,
        evaluation_after=_DUMMY_EVAL,
        classification=classification,
        centipawn_loss=centipawn_loss,
        candidate_moves=candidates,
        insight=None,
    )


analyzed_move_lists = st.lists(analyzed_move(), min_size=0, max_size=60)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestLearningSummaryCompleteness:
    """Property 12: Learning Summary Includes All Suboptimal Moves."""

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_includes_all_suboptimal_moves(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """Every inaccuracy/mistake/blunder with centipawn_loss appears in the summary.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        expected_suboptimal = [
            m for m in moves
            if m.classification in _SUBOPTIMAL and m.centipawn_loss is not None
        ]

        assert len(summary) == len(expected_suboptimal)

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_excludes_best_excellent_good(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """No move classified as best, excellent, or good appears in the summary.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        for insight in summary:
            assert isinstance(insight, LearningInsight)
            assert insight.classification not in _OPTIMAL

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_excludes_none_classification(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """Moves with no classification (None) do not appear in the summary.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        for insight in summary:
            assert isinstance(insight, LearningInsight)
            assert insight.classification is not None

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_insights_have_explanations(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """Every insight in the summary has a non-empty explanation.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        for insight in summary:
            assert isinstance(insight, LearningInsight)
            assert isinstance(insight.explanation, str)
            assert len(insight.explanation) > 0

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_preserves_move_order(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """Insights appear in the same order as their moves in the input list.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        expected_suboptimal = [
            m for m in moves
            if m.classification in _SUBOPTIMAL and m.centipawn_loss is not None
        ]

        assert len(summary) == len(expected_suboptimal)
        for insight, move in zip(summary, expected_suboptimal):
            assert insight.move_number == move.move_number
            assert insight.is_white == move.is_white
            assert insight.played_move == move.move_san

    @given(moves=analyzed_move_lists)
    @settings(max_examples=100)
    def test_summary_insight_classifications_are_suboptimal(
        self, moves: list[AnalyzedMove],
    ) -> None:
        """Every insight classification is one of inaccuracy, mistake, or blunder.

        **Validates: Requirements 9.4**
        """
        summary = generate_learning_summary(moves)

        for insight in summary:
            assert insight.classification in _SUBOPTIMAL
