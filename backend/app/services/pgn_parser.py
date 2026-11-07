"""PGN parser and formatter using python-chess.

Provides functions to parse PGN strings into structured ParsedGame objects
and format ParsedGame objects back into PGN export-format strings.
"""

import io

import chess
import chess.pgn

from app.models import ParsedGame

# Seven Tag Roster header names per the PGN standard.
SEVEN_TAG_ROSTER = frozenset(
    ["Event", "Site", "Date", "Round", "White", "Black", "Result"]
)


class PGNParseError(Exception):
    """Raised when PGN parsing fails.

    Attributes:
        message: Human-readable description of the failure.
        location: Where in the PGN the error occurred
                  (e.g., ``"move 5"`` or a header name).
    """

    def __init__(self, message: str, location: str | None = None) -> None:
        self.message = message
        self.location = location
        super().__init__(message)


class _ErrorTrackingVisitor(chess.pgn.GameBuilder):
    """Game builder that collects move-parsing errors with location info."""

    def __init__(self) -> None:
        super().__init__()
        self.errors: list[tuple[int, str]] = []
        self._half_move_count: int = 0

    def visit_move(self, board: chess.Board, move: chess.Move) -> None:
        self._half_move_count += 1
        return super().visit_move(board, move)

    def handle_error(self, error: Exception) -> None:
        """Record the error together with the half-move index where it occurred."""
        self.errors.append((self._half_move_count, str(error)))


def parse_pgn(pgn_string: str) -> ParsedGame:
    """Parse a PGN string into a structured :class:`ParsedGame`.

    Extracts the Seven Tag Roster, any additional tag pairs, the SAN
    move list, per-move comments, and the FEN after each half-move.

    Args:
        pgn_string: A PGN-formatted string.

    Returns:
        A fully populated :class:`ParsedGame`.

    Raises:
        PGNParseError: If the input is empty, malformed, contains
            invalid moves, or has no moves after the header section.
    """
    if not pgn_string or not pgn_string.strip():
        raise PGNParseError("Empty PGN string provided")

    pgn_io = io.StringIO(pgn_string)
    visitor = _ErrorTrackingVisitor()

    try:
        game = chess.pgn.read_game(pgn_io, Visitor=lambda: visitor)
    except Exception as exc:
        raise PGNParseError(f"Failed to parse PGN: {exc}") from exc

    if game is None:
        raise PGNParseError("Failed to parse PGN: no valid game data found")

    # Report the first error with a move-number location.
    if visitor.errors:
        half_move_idx, error_msg = visitor.errors[0]
        move_number = (half_move_idx // 2) + 1
        raise PGNParseError(
            f"Invalid move at move {move_number}: {error_msg}",
            location=f"move {move_number}",
        )

    # --- Seven Tag Roster ------------------------------------------------
    headers = game.headers
    event = headers.get("Event", "?")
    site = headers.get("Site", "?")
    date = headers.get("Date", "????.??.??")
    round_ = headers.get("Round", "?")
    white = headers.get("White", "?")
    black = headers.get("Black", "?")
    result = headers.get("Result", "*")

    # --- Additional headers -----------------------------------------------
    additional_headers: dict[str, str] = {
        key: value
        for key, value in headers.items()
        if key not in SEVEN_TAG_ROSTER
    }

    # --- Mainline moves, comments, FENs -----------------------------------
    board = game.board()
    moves: list[str] = []
    comments: list[str | None] = []
    fens: list[str] = []

    for node in game.mainline():
        san = board.san(node.move)
        moves.append(san)
        comments.append(node.comment if node.comment else None)
        board.push(node.move)
        fens.append(board.fen())

    # Requirement 4.5: reject PGN with an empty move section.
    if not moves:
        raise PGNParseError(
            "No moves found in PGN",
            location="moves",
        )

    return ParsedGame(
        event=event,
        site=site,
        date=date,
        round=round_,
        white=white,
        black=black,
        result=result,
        additional_headers=additional_headers,
        moves=moves,
        comments=comments,
        fens=fens,
    )


def format_pgn(game: ParsedGame) -> str:
    """Format a :class:`ParsedGame` into a PGN export-format string.

    Produces a string conforming to the PGN standard with the Seven Tag
    Roster, additional tag pairs, movetext with comments, and the game
    termination marker.

    Args:
        game: A structured game representation.

    Returns:
        A PGN-formatted string.
    """
    chess_game = chess.pgn.Game()

    # Seven Tag Roster
    chess_game.headers["Event"] = game.event
    chess_game.headers["Site"] = game.site
    chess_game.headers["Date"] = game.date
    chess_game.headers["Round"] = game.round
    chess_game.headers["White"] = game.white
    chess_game.headers["Black"] = game.black
    chess_game.headers["Result"] = game.result

    # Additional headers
    for key, value in game.additional_headers.items():
        chess_game.headers[key] = value

    # Replay the move list on a fresh board and build the game tree.
    node = chess_game
    board = chess_game.board()

    for i, san in enumerate(game.moves):
        move = board.parse_san(san)
        node = node.add_variation(move)
        if i < len(game.comments) and game.comments[i]:
            node.comment = game.comments[i]
        board.push(move)

    # Export to a PGN string.
    exporter = chess.pgn.StringExporter(
        headers=True,
        variations=False,
        comments=True,
    )
    return chess_game.accept(exporter)
