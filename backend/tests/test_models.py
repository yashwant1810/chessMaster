"""Unit tests for domain models and enums."""

from datetime import datetime

from app.models import (
    AnalysisStatus,
    AnalyzedMove,
    CandidateMove,
    GameAnalysis,
    GameResult,
    GameSummary,
    LearningInsight,
    MoveClassification,
    ParsedGame,
    PlayerAnalysisSummary,
    PositionEvaluation,
)


class TestMoveClassification:
    """Tests for MoveClassification enum."""

    def test_has_six_members(self) -> None:
        assert len(MoveClassification) == 6

    def test_values(self) -> None:
        assert MoveClassification.BEST.value == "best"
        assert MoveClassification.EXCELLENT.value == "excellent"
        assert MoveClassification.GOOD.value == "good"
        assert MoveClassification.INACCURACY.value == "inaccuracy"
        assert MoveClassification.MISTAKE.value == "mistake"
        assert MoveClassification.BLUNDER.value == "blunder"

    def test_lookup_by_value(self) -> None:
        assert MoveClassification("best") is MoveClassification.BEST
        assert MoveClassification("blunder") is MoveClassification.BLUNDER


class TestGameResult:
    """Tests for GameResult enum."""

    def test_has_three_members(self) -> None:
        assert len(GameResult) == 3

    def test_values(self) -> None:
        assert GameResult.WIN.value == "win"
        assert GameResult.LOSS.value == "loss"
        assert GameResult.DRAW.value == "draw"


class TestParsedGame:
    """Tests for ParsedGame dataclass."""

    def test_required_fields(self) -> None:
        game = ParsedGame(
            event="Test",
            site="chess.com",
            date="2024.01.01",
            round="1",
            white="player1",
            black="player2",
            result="1-0",
        )
        assert game.event == "Test"
        assert game.white == "player1"
        assert game.result == "1-0"

    def test_default_fields(self) -> None:
        game = ParsedGame(
            event="", site="", date="", round="",
            white="", black="", result="",
        )
        assert game.additional_headers == {}
        assert game.moves == []
        assert game.comments == []
        assert game.fens == []

    def test_default_fields_are_independent(self) -> None:
        """Ensure mutable defaults are not shared between instances."""
        game1 = ParsedGame(
            event="", site="", date="", round="",
            white="", black="", result="",
        )
        game2 = ParsedGame(
            event="", site="", date="", round="",
            white="", black="", result="",
        )
        game1.moves.append("e4")
        assert game2.moves == []


class TestGameSummary:
    """Tests for GameSummary dataclass."""

    def test_fields(self) -> None:
        now = datetime.now()
        summary = GameSummary(
            game_id="abc123",
            date_played=now,
            opponent="opponent",
            result=GameResult.WIN,
            time_control="600",
            opening_name="Sicilian Defense",
            is_analyzed=False,
        )
        assert summary.game_id == "abc123"
        assert summary.date_played == now
        assert summary.result == GameResult.WIN
        assert summary.time_control == "600"
        assert summary.is_analyzed is False

    def test_nullable_fields(self) -> None:
        summary = GameSummary(
            game_id="abc",
            date_played=datetime.now(),
            opponent="opp",
            result=GameResult.DRAW,
            time_control=None,
            opening_name=None,
            is_analyzed=True,
        )
        assert summary.time_control is None
        assert summary.opening_name is None


class TestPositionEvaluation:
    """Tests for PositionEvaluation dataclass."""

    def test_centipawn_evaluation(self) -> None:
        pos = PositionEvaluation(
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            evaluation=30,
            mate_in=None,
            candidate_moves=[],
        )
        assert pos.evaluation == 30
        assert pos.mate_in is None
        assert pos.is_error is False

    def test_mate_evaluation(self) -> None:
        pos = PositionEvaluation(
            fen="some_fen",
            evaluation=None,
            mate_in=3,
            candidate_moves=[],
        )
        assert pos.evaluation is None
        assert pos.mate_in == 3

    def test_error_position(self) -> None:
        pos = PositionEvaluation(
            fen="invalid",
            evaluation=None,
            mate_in=None,
            candidate_moves=[],
            is_error=True,
        )
        assert pos.is_error is True


class TestCandidateMove:
    """Tests for CandidateMove dataclass."""

    def test_fields(self) -> None:
        move = CandidateMove(move_san="Nf3", evaluation=45, mate_in=None)
        assert move.move_san == "Nf3"
        assert move.evaluation == 45
        assert move.mate_in is None

    def test_mate_candidate(self) -> None:
        move = CandidateMove(move_san="Qh7#", evaluation=None, mate_in=1)
        assert move.mate_in == 1


class TestAnalyzedMove:
    """Tests for AnalyzedMove dataclass."""

    def test_fields(self) -> None:
        candidate = CandidateMove(move_san="e4", evaluation=20, mate_in=None)
        eval_before = PositionEvaluation(
            fen="start", evaluation=0, mate_in=None, candidate_moves=[candidate],
        )
        eval_after = PositionEvaluation(
            fen="after", evaluation=20, mate_in=None, candidate_moves=[],
        )
        move = AnalyzedMove(
            move_number=1,
            is_white=True,
            move_san="e4",
            position_before="start",
            position_after="after",
            evaluation_before=eval_before,
            evaluation_after=eval_after,
            classification=MoveClassification.BEST,
            centipawn_loss=0,
            candidate_moves=[candidate],
            insight=None,
        )
        assert move.move_number == 1
        assert move.is_white is True
        assert move.classification == MoveClassification.BEST
        assert move.insight is None


class TestLearningInsight:
    """Tests for LearningInsight dataclass."""

    def test_fields(self) -> None:
        insight = LearningInsight(
            move_number=10,
            is_white=False,
            played_move="Bxf7",
            best_move="Nc6",
            centipawn_loss=150,
            classification=MoveClassification.MISTAKE,
            principal_variation=["Nc6", "d4", "e5", "Nf3", "Bd6"],
            explanation="Nc6 develops the knight and controls the center.",
        )
        assert insight.centipawn_loss == 150
        assert insight.classification == MoveClassification.MISTAKE
        assert len(insight.principal_variation) == 5


class TestGameAnalysis:
    """Tests for GameAnalysis dataclass."""

    def test_fields(self) -> None:
        summary = PlayerAnalysisSummary(
            best_count=5, excellent_count=3, good_count=4,
            inaccuracy_count=2, mistake_count=1, blunder_count=0,
            performance_ratings=[1500], final_performance_rating=1500,
        )
        analysis = GameAnalysis(
            game_id="game1",
            moves=[],
            white_summary=summary,
            black_summary=summary,
            evaluations=[20, -10, 30],
            is_complete=True,
        )
        assert analysis.game_id == "game1"
        assert analysis.is_complete is True
        assert len(analysis.evaluations) == 3


class TestPlayerAnalysisSummary:
    """Tests for PlayerAnalysisSummary dataclass."""

    def test_fields(self) -> None:
        summary = PlayerAnalysisSummary(
            best_count=10,
            excellent_count=5,
            good_count=8,
            inaccuracy_count=3,
            mistake_count=2,
            blunder_count=1,
            performance_ratings=[1400, 1450, 1500],
            final_performance_rating=1500,
        )
        assert summary.best_count == 10
        assert summary.blunder_count == 1
        assert summary.final_performance_rating == 1500
        assert len(summary.performance_ratings) == 3


class TestAnalysisStatus:
    """Tests for AnalysisStatus dataclass."""

    def test_percentage_calculation(self) -> None:
        status = AnalysisStatus(
            game_id="abc",
            total_positions=40,
            positions_analyzed=20,
            is_complete=False,
        )
        assert status.percentage == 50

    def test_percentage_zero_total(self) -> None:
        status = AnalysisStatus(
            game_id="abc",
            total_positions=0,
            positions_analyzed=0,
            is_complete=False,
        )
        assert status.percentage == 0

    def test_percentage_complete(self) -> None:
        status = AnalysisStatus(
            game_id="abc",
            total_positions=80,
            positions_analyzed=80,
            is_complete=True,
        )
        assert status.percentage == 100

    def test_percentage_truncates(self) -> None:
        """Percentage uses int() truncation, not rounding."""
        status = AnalysisStatus(
            game_id="abc",
            total_positions=3,
            positions_analyzed=1,
            is_complete=False,
        )
        # 1/3 = 0.333... → int(33.3...) = 33
        assert status.percentage == 33
