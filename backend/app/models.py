"""Domain models and enums for the Chess Review Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MoveClassification(Enum):
    """Classification of a chess move based on centipawn loss thresholds.

    Thresholds:
        BEST:       cp_loss == 0
        EXCELLENT:  1 <= cp_loss <= 10
        GOOD:       11 <= cp_loss <= 30
        INACCURACY: 31 <= cp_loss <= 80
        MISTAKE:    81 <= cp_loss <= 200
        BLUNDER:    cp_loss >= 201
    """

    BEST = "best"
    EXCELLENT = "excellent"
    GOOD = "good"
    INACCURACY = "inaccuracy"
    MISTAKE = "mistake"
    BLUNDER = "blunder"


class GameResult(Enum):
    """Result of a chess game from the fetched player's perspective."""

    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


@dataclass
class ParsedGame:
    """Structured representation of a chess game parsed from PGN.

    Contains the Seven Tag Roster (required PGN headers), any additional
    tag pairs, the move list in SAN notation, per-move comments, and
    FEN strings after each half-move.
    """

    # Seven Tag Roster (required PGN headers)
    event: str
    site: str
    date: str
    round: str
    white: str
    black: str
    result: str
    # Additional headers
    additional_headers: dict[str, str] = field(default_factory=dict)
    # Move data
    moves: list[str] = field(default_factory=list)  # SAN notation
    comments: list[str | None] = field(default_factory=list)  # Per-move comments
    fens: list[str] = field(default_factory=list)  # FEN after each half-move


@dataclass
class GameSummary:
    """Summary info for game list display."""

    game_id: str
    date_played: datetime
    opponent: str
    result: GameResult
    time_control: str | None
    opening_name: str | None
    is_analyzed: bool


@dataclass
class PositionEvaluation:
    """Stockfish evaluation of a single position."""

    fen: str
    evaluation: int | None  # Centipawns from White's perspective
    mate_in: int | None  # Mate-in-N (positive=White, negative=Black)
    candidate_moves: list["CandidateMove"]  # Up to 3
    is_error: bool = False


@dataclass
class CandidateMove:
    """A candidate move suggested by Stockfish."""

    move_san: str
    evaluation: int | None  # Centipawns
    mate_in: int | None


@dataclass
class AnalyzedMove:
    """A single analyzed half-move in the game."""

    move_number: int
    is_white: bool
    move_san: str
    position_before: str  # FEN
    position_after: str  # FEN
    evaluation_before: PositionEvaluation
    evaluation_after: PositionEvaluation
    classification: MoveClassification | None
    centipawn_loss: int | None
    candidate_moves: list[CandidateMove]
    insight: "LearningInsight | None"


@dataclass
class LearningInsight:
    """Explanation for a suboptimal move."""

    move_number: int
    is_white: bool
    played_move: str
    best_move: str
    centipawn_loss: int
    classification: MoveClassification
    principal_variation: list[str]  # Up to 5 moves
    explanation: str


@dataclass
class GameAnalysis:
    """Complete analysis results for a game."""

    game_id: str
    moves: list[AnalyzedMove]
    white_summary: "PlayerAnalysisSummary"
    black_summary: "PlayerAnalysisSummary"
    evaluations: list[int | None]  # Centipawn per half-move for graph
    is_complete: bool


@dataclass
class PlayerAnalysisSummary:
    """Per-player summary of analysis results."""

    best_count: int
    excellent_count: int
    good_count: int
    inaccuracy_count: int
    mistake_count: int
    blunder_count: int
    performance_ratings: list[int]  # Cumulative after each of player's moves
    final_performance_rating: int


@dataclass
class AnalysisStatus:
    """Progress of an ongoing analysis."""

    game_id: str
    total_positions: int
    positions_analyzed: int
    is_complete: bool

    @property
    def percentage(self) -> int:
        """Return analysis progress as a percentage (0–100)."""
        if self.total_positions == 0:
            return 0
        return int((self.positions_analyzed / self.total_positions) * 100)


@dataclass
class FetchResult:
    """Result of a game fetch operation.

    Attributes:
        username: The chess.com username that was fetched.
        games_fetched: Number of games successfully fetched and stored.
        is_capped: True when the 10,000 game limit was reached.
        message: Optional human-readable status message (e.g.,
            ``"No games found for this username"``).
    """

    username: str
    games_fetched: int
    is_capped: bool = False
    message: str | None = None
