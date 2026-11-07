"""Property tests for malformed PGN error reporting.

Feature: chess-review-engine, Property 2: Malformed PGN error reporting

**Validates: Requirements 4.4**

Generates random invalid PGN strings across four categories and verifies
that ``parse_pgn`` always raises ``PGNParseError`` (never silently returns
a ``ParsedGame``) and, where applicable, includes meaningful location info.
"""

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app.services.pgn_parser import PGNParseError, parse_pgn


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_HEADERS = """\
[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "?"]
[White "Player1"]
[Black "Player2"]
[Result "*"]"""

REFERENCE_GAME_PGN = """\
[Event "Test"]
[Site "?"]
[Date "2024.01.01"]
[Round "?"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0"""


# ---------------------------------------------------------------------------
# Strategy 1 – Empty or whitespace-only strings
# ---------------------------------------------------------------------------

@st.composite
def empty_or_whitespace(draw: st.DrawFn) -> str:
    """Generate empty strings or strings containing only whitespace."""
    return draw(
        st.text(
            alphabet=st.sampled_from(list(" \t\n\r")),
            min_size=0,
            max_size=20,
        )
    )


# ---------------------------------------------------------------------------
# Strategy 2 – Valid headers + garbage move section
# ---------------------------------------------------------------------------

# Characters that cannot form valid SAN, PGN move numbers, or results.
_GARBAGE_ALPHABET = list("!@#$%^&*~`|")


@st.composite
def headers_plus_garbage(draw: st.DrawFn) -> str:
    """Valid Seven-Tag-Roster headers followed by non-chess garbage text."""
    garbage = draw(
        st.text(alphabet=st.sampled_from(_GARBAGE_ALPHABET), min_size=3, max_size=60)
    )
    return f"{VALID_HEADERS}\n\n{garbage}"


# ---------------------------------------------------------------------------
# Strategy 3 – Truncated PGN (cut off mid-stream)
# ---------------------------------------------------------------------------

@st.composite
def truncated_pgn(draw: st.DrawFn) -> str:
    """Cut a valid PGN at a random point inside the header section.

    Truncating within headers guarantees the PGN is structurally
    incomplete — no valid movetext can be reached.
    """
    header_end = REFERENCE_GAME_PGN.index("\n\n")
    cut = draw(st.integers(min_value=1, max_value=header_end))
    return REFERENCE_GAME_PGN[:cut]


# ---------------------------------------------------------------------------
# Strategy 4 – PGN with illegal moves inserted
# ---------------------------------------------------------------------------

# Structurally valid SAN that is *illegal* from the starting position
# (all squares are blocked by own pieces or unreachable).
ILLEGAL_VALID_SAN = [
    "Qd2",  # Queen d1→d2 blocked by pawn
    "Qe2",  # Queen d1→e2 blocked by pawn
    "Qh5",  # Queen d1→h5 blocked by e2 pawn
    "Bd3",  # c1/f1 bishops both blocked by pawns
    "Bf4",  # c1 bishop blocked by d2 pawn
    "Ra2",  # a1 rook blocked by a2 pawn
    "Rh2",  # h1 rook blocked by h2 pawn
    "Ke2",  # King e1→e2 blocked by pawn
    "Kd1",  # King e1→d1 occupied by own queen
    "Kf1",  # King e1→f1 occupied by own bishop
]

# Tokens that aren't valid SAN at all.
INVALID_SAN_TOKENS = [
    "Zz1",   # No such piece / square
    "Xx9",   # Invalid file and rank
    "e9",    # Rank 9 doesn't exist
    "j4",    # File j doesn't exist
    "hello", # Plain text
]

ALL_ILLEGAL_MOVES = ILLEGAL_VALID_SAN + INVALID_SAN_TOKENS


@st.composite
def headers_with_illegal_move(draw: st.DrawFn) -> str:
    """Valid headers followed by a single illegal or nonsensical move."""
    illegal = draw(st.sampled_from(ALL_ILLEGAL_MOVES))
    return f"{VALID_HEADERS}\n\n1. {illegal} *"


# ---------------------------------------------------------------------------
# Combined strategy
# ---------------------------------------------------------------------------

malformed_pgn_strategy = st.one_of(
    empty_or_whitespace(),
    headers_plus_garbage(),
    truncated_pgn(),
    headers_with_illegal_move(),
)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestMalformedPGNErrorReporting:
    """Property 2: Malformed PGN Error Reporting.

    For any string that is not a valid PGN (containing invalid move
    notation, missing required headers, or structural errors), the PGN
    parser SHALL return an error rather than a successful parse, and that
    error SHALL identify the location where parsing failed.

    **Validates: Requirements 4.4**
    """

    @given(pgn=malformed_pgn_strategy)
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_malformed_pgn_always_raises_error(self, pgn: str) -> None:
        """Any malformed PGN must raise PGNParseError, never return a ParsedGame.

        **Validates: Requirements 4.4**
        """
        with pytest.raises(PGNParseError):
            parse_pgn(pgn)

    @given(illegal=st.sampled_from(ILLEGAL_VALID_SAN))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_illegal_move_error_includes_move_location(self, illegal: str) -> None:
        """Illegal-but-structurally-valid SAN must produce an error with
        move-number location info.

        **Validates: Requirements 4.4**
        """
        pgn = f"{VALID_HEADERS}\n\n1. {illegal} *"
        with pytest.raises(PGNParseError) as exc_info:
            parse_pgn(pgn)
        err = exc_info.value
        assert err.location is not None, (
            f"Error '{err.message}' missing location for illegal move '{illegal}'"
        )
        assert "move" in err.location.lower(), (
            f"Location '{err.location}' should reference a move number"
        )

    @given(result=st.sampled_from(["*", "1-0", "0-1", "1/2-1/2"]))
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_no_moves_error_references_moves_location(self, result: str) -> None:
        """PGN with valid headers but only a result marker must report
        location as ``'moves'``.

        **Validates: Requirements 4.4**
        """
        headers = (
            '[Event "Test"]\n'
            '[Site "?"]\n'
            '[Date "2024.01.01"]\n'
            '[Round "?"]\n'
            '[White "Player1"]\n'
            '[Black "Player2"]\n'
            f'[Result "{result}"]'
        )
        pgn = f"{headers}\n\n{result}"
        with pytest.raises(PGNParseError) as exc_info:
            parse_pgn(pgn)
        assert exc_info.value.location == "moves", (
            f"Expected location='moves', got '{exc_info.value.location}'"
        )

    @given(pgn=empty_or_whitespace())
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    def test_empty_input_reports_empty_pgn_error(self, pgn: str) -> None:
        """Empty or whitespace-only input must produce an 'Empty PGN' error.

        **Validates: Requirements 4.4**
        """
        with pytest.raises(PGNParseError, match="Empty PGN"):
            parse_pgn(pgn)
