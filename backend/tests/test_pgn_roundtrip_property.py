"""Property-based test for PGN round-trip fidelity.

**Validates: Requirements 4.1, 4.2, 4.3**

Property 1 – PGN Round-Trip Fidelity:
    For any valid PGN string, parsing it into a structured game
    representation, formatting that representation back into a PGN
    string, and re-parsing the result SHALL produce a structured
    representation with the same move sequence, Seven Tag Roster header
    values, additional tag pair values, and comment annotations as the
    original parse.
"""

import chess
import chess.pgn
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.pgn_parser import format_pgn, parse_pgn

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Printable text safe for PGN header values: no double-quotes, no
# backslashes, no newlines (these would break PGN tag-pair syntax).
_safe_header_chars = st.characters(
    whitelist_categories=("L", "N", "P", "S", "Z"),
    blacklist_characters='"\\{}\n\r',
)
_safe_header_text = st.text(_safe_header_chars, min_size=1, max_size=30)

# PGN result tokens.
_results = st.sampled_from(["1-0", "0-1", "1/2-1/2", "*"])

# PGN date format (YYYY.MM.DD or the unknown placeholder).
_dates = st.sampled_from(
    [
        "2024.01.15",
        "2023.12.31",
        "2000.06.01",
        "????.??.??",
        "2024.??.??",
    ]
)

# Comment text safe inside PGN { } annotations.
# Must contain at least one visible (non-whitespace) character so that
# python-chess does not strip the comment to empty on round-trip.
_safe_comment_chars = st.characters(
    whitelist_categories=("L", "N", "P"),
    blacklist_characters='{}\n\r',
)
_comment_text = st.text(_safe_comment_chars, min_size=1, max_size=60).filter(
    lambda s: s.strip() != ""
)

# Additional header keys that do NOT collide with the Seven Tag Roster.
_SEVEN_TAG_ROSTER = frozenset(
    ["Event", "Site", "Date", "Round", "White", "Black", "Result"]
)

_extra_header_key = st.sampled_from(
    ["ECO", "TimeControl", "Opening", "WhiteElo", "BlackElo", "Annotator"]
)

_extra_headers = st.dictionaries(
    keys=_extra_header_key,
    values=_safe_header_text,
    min_size=0,
    max_size=4,
)


@st.composite
def valid_pgn_games(draw: st.DrawFn) -> str:
    """Generate a syntactically valid PGN string with random legal moves,
    headers, and optional per-move comments.

    Uses ``chess.Board`` to guarantee every move is legal, then assembles
    a well-formed PGN string from the components.
    """
    # --- Seven Tag Roster --------------------------------------------------
    event = draw(_safe_header_text)
    site = draw(_safe_header_text)
    date = draw(_dates)
    round_ = draw(_safe_header_text)
    white = draw(_safe_header_text)
    black = draw(_safe_header_text)
    result = draw(_results)

    # --- Additional headers ------------------------------------------------
    additional = draw(_extra_headers)

    # --- Legal move sequence -----------------------------------------------
    num_moves = draw(st.integers(min_value=1, max_value=40))
    board = chess.Board()
    san_moves: list[str] = []

    for _ in range(num_moves):
        legal = list(board.legal_moves)
        if not legal or board.is_game_over():
            break
        move = draw(st.sampled_from(legal))
        san_moves.append(board.san(move))
        board.push(move)

    # Guarantee at least one move (parse_pgn rejects empty move sections).
    if not san_moves:
        board = chess.Board()
        first_move = draw(st.sampled_from(list(board.legal_moves)))
        san_moves.append(board.san(first_move))

    # --- Per-move comments (sparse) ----------------------------------------
    comments: list[str | None] = []
    for _ in san_moves:
        has_comment = draw(st.booleans())
        if has_comment:
            comments.append(draw(_comment_text))
        else:
            comments.append(None)

    # --- Build PGN string --------------------------------------------------
    lines: list[str] = []
    lines.append(f'[Event "{event}"]')
    lines.append(f'[Site "{site}"]')
    lines.append(f'[Date "{date}"]')
    lines.append(f'[Round "{round_}"]')
    lines.append(f'[White "{white}"]')
    lines.append(f'[Black "{black}"]')
    lines.append(f'[Result "{result}"]')
    for key, value in additional.items():
        lines.append(f'[{key} "{value}"]')
    lines.append("")

    # Movetext
    movetext_parts: list[str] = []
    for i, san in enumerate(san_moves):
        if i % 2 == 0:
            movetext_parts.append(f"{i // 2 + 1}.")
        movetext_parts.append(san)
        if comments[i] is not None:
            movetext_parts.append(f"{{{comments[i]}}}")

    movetext_parts.append(result)
    lines.append(" ".join(movetext_parts))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


@given(pgn=valid_pgn_games())
@settings(max_examples=150, deadline=None)
def test_pgn_round_trip_fidelity(pgn: str) -> None:
    """**Validates: Requirements 4.1, 4.2, 4.3**

    parse_pgn(format_pgn(parse_pgn(pgn))) == parse_pgn(pgn)

    Specifically, the move sequence, Seven Tag Roster values, additional
    header values, and per-move comments must be identical after a full
    parse → format → re-parse cycle.
    """
    original = parse_pgn(pgn)
    formatted = format_pgn(original)
    reparsed = parse_pgn(formatted)

    # Move sequence
    assert reparsed.moves == original.moves, (
        f"Moves differ:\n  original: {original.moves}\n  reparsed: {reparsed.moves}"
    )

    # Seven Tag Roster
    assert reparsed.event == original.event
    assert reparsed.site == original.site
    assert reparsed.date == original.date
    assert reparsed.round == original.round
    assert reparsed.white == original.white
    assert reparsed.black == original.black
    assert reparsed.result == original.result

    # Additional headers
    assert reparsed.additional_headers == original.additional_headers, (
        f"Additional headers differ:\n"
        f"  original: {original.additional_headers}\n"
        f"  reparsed: {reparsed.additional_headers}"
    )

    # Comments
    assert reparsed.comments == original.comments, (
        f"Comments differ:\n"
        f"  original: {original.comments}\n"
        f"  reparsed: {reparsed.comments}"
    )
