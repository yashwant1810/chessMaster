"""Unit tests for the PGN parser and formatter."""

import pytest

from app.models import ParsedGame
from app.services.pgn_parser import PGNParseError, format_pgn, parse_pgn


# ---------------------------------------------------------------------------
# Sample PGN fixtures
# ---------------------------------------------------------------------------

SAMPLE_PGN = """\
[Event "Rated Blitz"]
[Site "Chess.com"]
[Date "2024.01.15"]
[Round "1"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"""

PGN_WITH_COMMENTS = """\
[Event "Training"]
[Site "Online"]
[Date "2024.03.10"]
[Round "?"]
[White "Coach"]
[Black "Student"]
[Result "1/2-1/2"]

1. d4 {Queen's pawn opening} d5 {Solid reply} 2. c4 {The Queen's Gambit} e6 1/2-1/2"""

PGN_WITH_ADDITIONAL_HEADERS = """\
[Event "Rapid"]
[Site "Chess.com"]
[Date "2024.06.01"]
[Round "3"]
[White "Player1"]
[Black "Player2"]
[Result "*"]
[ECO "C60"]
[TimeControl "600+5"]
[Opening "Ruy Lopez"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 *"""

PGN_NO_MOVES = """\
[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]

*"""

PGN_INVALID_MOVE = """\
[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]

1. e4 e5 2. Qh8 *"""

PGN_SHORT_GAME = """\
[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]

1. e4 *"""


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


class TestParsePGN:
    """Tests for parse_pgn()."""

    def test_parse_seven_tag_roster(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        assert game.event == "Rated Blitz"
        assert game.site == "Chess.com"
        assert game.date == "2024.01.15"
        assert game.round == "1"
        assert game.white == "Alice"
        assert game.black == "Bob"
        assert game.result == "1-0"

    def test_parse_moves(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        assert game.moves == ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]

    def test_parse_fens_count(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        # One FEN per half-move
        assert len(game.fens) == len(game.moves) == 6

    def test_parse_fen_content(self) -> None:
        """First FEN should reflect 1. e4."""
        game = parse_pgn(SAMPLE_PGN)
        fen = game.fens[0]
        # After 1. e4 the pawn is on e4, Black to move
        assert " b " in fen  # Black to move
        # e4 pawn present (rank 4)
        parts = fen.split(" ")
        assert "P" in parts[0]  # White pawn exists in the position

    def test_parse_comments(self) -> None:
        game = parse_pgn(PGN_WITH_COMMENTS)
        assert game.comments[0] == "Queen's pawn opening"
        assert game.comments[1] == "Solid reply"
        assert game.comments[2] == "The Queen's Gambit"
        assert game.comments[3] is None  # 2...e6 has no comment

    def test_parse_comments_length_matches_moves(self) -> None:
        game = parse_pgn(PGN_WITH_COMMENTS)
        assert len(game.comments) == len(game.moves)

    def test_parse_additional_headers(self) -> None:
        game = parse_pgn(PGN_WITH_ADDITIONAL_HEADERS)
        assert game.additional_headers["ECO"] == "C60"
        assert game.additional_headers["TimeControl"] == "600+5"
        assert game.additional_headers["Opening"] == "Ruy Lopez"

    def test_seven_tag_roster_not_in_additional_headers(self) -> None:
        game = parse_pgn(PGN_WITH_ADDITIONAL_HEADERS)
        for key in ("Event", "Site", "Date", "Round", "White", "Black", "Result"):
            assert key not in game.additional_headers

    def test_parse_single_move_game(self) -> None:
        game = parse_pgn(PGN_SHORT_GAME)
        assert game.moves == ["e4"]
        assert len(game.fens) == 1
        assert len(game.comments) == 1

    def test_no_comments_returns_none_entries(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        assert all(c is None for c in game.comments)


# ---------------------------------------------------------------------------
# Formatting tests
# ---------------------------------------------------------------------------


class TestFormatPGN:
    """Tests for format_pgn()."""

    def test_format_includes_headers(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        pgn = format_pgn(game)
        assert '[Event "Rated Blitz"]' in pgn
        assert '[White "Alice"]' in pgn
        assert '[Black "Bob"]' in pgn
        assert '[Result "1-0"]' in pgn

    def test_format_includes_moves(self) -> None:
        game = parse_pgn(SAMPLE_PGN)
        pgn = format_pgn(game)
        assert "e4" in pgn
        assert "Bb5" in pgn
        assert "1-0" in pgn

    def test_format_includes_comments(self) -> None:
        game = parse_pgn(PGN_WITH_COMMENTS)
        pgn = format_pgn(game)
        assert "Queen's pawn opening" in pgn
        assert "Solid reply" in pgn
        assert "The Queen's Gambit" in pgn

    def test_format_includes_additional_headers(self) -> None:
        game = parse_pgn(PGN_WITH_ADDITIONAL_HEADERS)
        pgn = format_pgn(game)
        assert '[ECO "C60"]' in pgn
        assert '[TimeControl "600+5"]' in pgn
        assert '[Opening "Ruy Lopez"]' in pgn


# ---------------------------------------------------------------------------
# Round-trip fidelity tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Tests verifying parse → format → re-parse fidelity (Requirement 4.3)."""

    def _assert_round_trip(self, pgn_text: str) -> None:
        original = parse_pgn(pgn_text)
        formatted = format_pgn(original)
        reparsed = parse_pgn(formatted)

        assert reparsed.moves == original.moves
        assert reparsed.event == original.event
        assert reparsed.site == original.site
        assert reparsed.date == original.date
        assert reparsed.round == original.round
        assert reparsed.white == original.white
        assert reparsed.black == original.black
        assert reparsed.result == original.result
        assert reparsed.additional_headers == original.additional_headers
        assert reparsed.comments == original.comments

    def test_round_trip_basic(self) -> None:
        self._assert_round_trip(SAMPLE_PGN)

    def test_round_trip_with_comments(self) -> None:
        self._assert_round_trip(PGN_WITH_COMMENTS)

    def test_round_trip_with_additional_headers(self) -> None:
        self._assert_round_trip(PGN_WITH_ADDITIONAL_HEADERS)

    def test_round_trip_short_game(self) -> None:
        self._assert_round_trip(PGN_SHORT_GAME)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestPGNParseErrors:
    """Tests for error reporting (Requirements 4.4, 4.5)."""

    def test_error_on_empty_string(self) -> None:
        with pytest.raises(PGNParseError, match="Empty PGN"):
            parse_pgn("")

    def test_error_on_whitespace_only(self) -> None:
        with pytest.raises(PGNParseError, match="Empty PGN"):
            parse_pgn("   \n\t  ")

    def test_error_on_no_moves(self) -> None:
        with pytest.raises(PGNParseError, match="No moves found") as exc_info:
            parse_pgn(PGN_NO_MOVES)
        assert exc_info.value.location == "moves"

    def test_error_on_invalid_move_has_location(self) -> None:
        """Illegal move Qh8 at move 2 should produce an error with location."""
        with pytest.raises(PGNParseError) as exc_info:
            parse_pgn(PGN_INVALID_MOVE)
        assert exc_info.value.location is not None
        assert "move" in exc_info.value.location

    def test_error_on_garbage_input(self) -> None:
        with pytest.raises(PGNParseError):
            parse_pgn("this is not a pgn at all")

    def test_error_preserves_location_attribute(self) -> None:
        try:
            parse_pgn(PGN_INVALID_MOVE)
            pytest.fail("Expected PGNParseError")
        except PGNParseError as exc:
            assert exc.location is not None
            assert exc.message is not None
