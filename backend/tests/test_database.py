"""Unit tests for the SQLite database access layer."""

import sqlite3

import pytest

from app.database import (
    get_analysis,
    get_analysis_summary,
    get_connection,
    get_game,
    init_db,
    insert_analysis_result,
    insert_game,
    list_games,
    upsert_analysis_summary,
)
from app.models import ParsedGame, PlayerAnalysisSummary


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn():
    """In-memory SQLite connection with schema initialized."""
    conn = get_connection(":memory:")
    conn.executescript(
        open(
            __import__("app.database", fromlist=["SCHEMA_SQL"]).__file__
        ).read()
        if False
        else ""
    )
    # Use the actual schema constant
    from app.database import SCHEMA_SQL

    conn.executescript(SCHEMA_SQL)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def sample_game() -> ParsedGame:
    """A minimal ParsedGame for testing."""
    return ParsedGame(
        event="Rated Blitz game",
        site="Chess.com",
        date="2024.01.15",
        round="-",
        white="player1",
        black="player2",
        result="1-0",
        additional_headers={"TimeControl": "300+3", "Opening": "Sicilian Defense"},
        moves=["e4", "c5", "Nf3", "d6"],
        comments=[None, None, "Good move", None],
        fens=[
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
            "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
            "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3",
        ],
    )


@pytest.fixture
def sample_white_summary() -> PlayerAnalysisSummary:
    return PlayerAnalysisSummary(
        best_count=5,
        excellent_count=3,
        good_count=2,
        inaccuracy_count=1,
        mistake_count=0,
        blunder_count=0,
        performance_ratings=[1500, 1520, 1540],
        final_performance_rating=1540,
    )


@pytest.fixture
def sample_black_summary() -> PlayerAnalysisSummary:
    return PlayerAnalysisSummary(
        best_count=4,
        excellent_count=2,
        good_count=3,
        inaccuracy_count=0,
        mistake_count=1,
        blunder_count=1,
        performance_ratings=[1400, 1380, 1350],
        final_performance_rating=1350,
    )


# ---------------------------------------------------------------------------
# Schema initialization
# ---------------------------------------------------------------------------


class TestInitDb:
    def test_creates_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        assert "games" in tables
        assert "analysis_results" in tables
        assert "analysis_summaries" in tables

    def test_creates_indexes(self, tmp_path):
        db_path = tmp_path / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        conn.close()

        assert "idx_games_username" in indexes
        assert "idx_games_date" in indexes
        assert "idx_analysis_game" in indexes

    def test_idempotent(self, tmp_path):
        """Calling init_db twice should not raise."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        init_db(db_path)  # Should not raise


# ---------------------------------------------------------------------------
# Game CRUD
# ---------------------------------------------------------------------------


class TestInsertAndGetGame:
    def test_insert_and_retrieve(self, db_conn, sample_game):
        insert_game(db_conn, "game-1", "testuser", "1. e4 c5 ...", sample_game)

        result = get_game(db_conn, "game-1")
        assert result is not None
        assert result["id"] == "game-1"
        assert result["username"] == "testuser"
        assert result["pgn_raw"] == "1. e4 c5 ..."
        assert result["white"] == "player1"
        assert result["black"] == "player2"
        assert result["result"] == "1-0"
        assert result["event"] == "Rated Blitz game"
        assert result["site"] == "Chess.com"
        assert result["date_played"] == "2024.01.15"

    def test_time_control_from_headers(self, db_conn, sample_game):
        insert_game(db_conn, "game-1", "testuser", "pgn", sample_game)
        result = get_game(db_conn, "game-1")
        assert result["time_control"] == "300+3"

    def test_opening_name_from_headers(self, db_conn, sample_game):
        insert_game(db_conn, "game-1", "testuser", "pgn", sample_game)
        result = get_game(db_conn, "game-1")
        assert result["opening_name"] == "Sicilian Defense"

    def test_explicit_time_control_overrides(self, db_conn, sample_game):
        insert_game(
            db_conn, "game-1", "testuser", "pgn", sample_game,
            time_control="600",
        )
        result = get_game(db_conn, "game-1")
        assert result["time_control"] == "600"

    def test_json_fields_deserialized(self, db_conn, sample_game):
        insert_game(db_conn, "game-1", "testuser", "pgn", sample_game)
        result = get_game(db_conn, "game-1")

        assert result["moves"] == ["e4", "c5", "Nf3", "d6"]
        assert result["comments"] == [None, None, "Good move", None]
        assert len(result["fens"]) == 4
        assert result["additional_headers"] == {
            "TimeControl": "300+3",
            "Opening": "Sicilian Defense",
        }

    def test_get_nonexistent_game(self, db_conn):
        assert get_game(db_conn, "no-such-game") is None

    def test_duplicate_game_id_raises(self, db_conn, sample_game):
        insert_game(db_conn, "game-1", "testuser", "pgn", sample_game)
        with pytest.raises(sqlite3.IntegrityError):
            insert_game(db_conn, "game-1", "testuser", "pgn2", sample_game)


# ---------------------------------------------------------------------------
# List games
# ---------------------------------------------------------------------------


class TestListGames:
    def _insert_games(self, conn, sample_game):
        """Insert three games with different dates and results."""
        g1 = ParsedGame(
            event="E1", site="S", date="2024.01.10", round="-",
            white="a", black="b", result="1-0",
            additional_headers={"TimeControl": "180"},
            moves=["e4"], fens=["fen1"],
        )
        g2 = ParsedGame(
            event="E2", site="S", date="2024.02.15", round="-",
            white="a", black="c", result="0-1",
            additional_headers={"TimeControl": "600"},
            moves=["d4"], fens=["fen2"],
        )
        g3 = ParsedGame(
            event="E3", site="S", date="2024.03.20", round="-",
            white="d", black="a", result="1/2-1/2",
            additional_headers={"TimeControl": "300"},
            moves=["c4"], fens=["fen3"],
        )
        insert_game(conn, "g1", "userA", "pgn1", g1)
        insert_game(conn, "g2", "userA", "pgn2", g2)
        insert_game(conn, "g3", "userB", "pgn3", g3)

    def test_list_all_games(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        games = list_games(db_conn)
        assert len(games) == 3

    def test_filter_by_username(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        games = list_games(db_conn, username="userA")
        assert len(games) == 2
        assert all(g["username"] == "userA" for g in games)

    def test_sort_by_date_desc(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        games = list_games(db_conn, sort_by="date_played", order="DESC")
        dates = [g["date_played"] for g in games]
        assert dates == sorted(dates, reverse=True)

    def test_sort_by_date_asc(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        games = list_games(db_conn, sort_by="date_played", order="ASC")
        dates = [g["date_played"] for g in games]
        assert dates == sorted(dates)

    def test_sort_by_result(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        games = list_games(db_conn, sort_by="result", order="ASC")
        results = [g["result"] for g in games]
        assert results == sorted(results)

    def test_invalid_sort_column_defaults_to_date(self, db_conn, sample_game):
        self._insert_games(db_conn, sample_game)
        # Should not raise; falls back to date_played
        games = list_games(db_conn, sort_by="invalid_column")
        assert len(games) == 3

    def test_empty_database(self, db_conn):
        games = list_games(db_conn)
        assert games == []


# ---------------------------------------------------------------------------
# Analysis result CRUD
# ---------------------------------------------------------------------------


class TestAnalysisResults:
    def _insert_test_game(self, conn):
        game = ParsedGame(
            event="E", site="S", date="2024.01.01", round="-",
            white="w", black="b", result="1-0",
            moves=["e4", "e5"], fens=["fen1", "fen2"],
        )
        insert_game(conn, "game-1", "user", "pgn", game)

    def test_insert_and_get_analysis(self, db_conn):
        self._insert_test_game(db_conn)

        insert_analysis_result(
            db_conn,
            game_id="game-1",
            move_index=0,
            is_white=True,
            move_san="e4",
            fen_before="startfen",
            fen_after="fen1",
            eval_before=15,
            eval_after=20,
            classification="best",
            centipawn_loss=0,
            candidate_moves=[
                {"move_san": "e4", "evaluation": 20, "mate_in": None},
                {"move_san": "d4", "evaluation": 18, "mate_in": None},
            ],
        )

        results = get_analysis(db_conn, "game-1")
        assert len(results) == 1

        r = results[0]
        assert r["game_id"] == "game-1"
        assert r["move_index"] == 0
        assert r["is_white"] is True
        assert r["move_san"] == "e4"
        assert r["eval_before"] == 15
        assert r["eval_after"] == 20
        assert r["classification"] == "best"
        assert r["centipawn_loss"] == 0
        assert len(r["candidate_moves"]) == 2
        assert r["candidate_moves"][0]["move_san"] == "e4"

    def test_multiple_moves_ordered(self, db_conn):
        self._insert_test_game(db_conn)

        # Insert out of order
        insert_analysis_result(
            db_conn, "game-1", move_index=1, is_white=False,
            move_san="e5", fen_before="f1", fen_after="f2",
        )
        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
        )

        results = get_analysis(db_conn, "game-1")
        assert len(results) == 2
        assert results[0]["move_index"] == 0
        assert results[1]["move_index"] == 1

    def test_replace_on_conflict(self, db_conn):
        """Re-inserting same (game_id, move_index) replaces the row."""
        self._insert_test_game(db_conn)

        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
            classification="good",
        )
        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
            classification="best",
        )

        results = get_analysis(db_conn, "game-1")
        assert len(results) == 1
        assert results[0]["classification"] == "best"

    def test_insight_stored_as_json(self, db_conn):
        self._insert_test_game(db_conn)

        insight_data = {
            "move_number": 1,
            "played_move": "e4",
            "best_move": "d4",
            "centipawn_loss": 15,
            "explanation": "d4 was slightly better",
        }
        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
            insight=insight_data,
        )

        results = get_analysis(db_conn, "game-1")
        assert results[0]["insight"] == insight_data

    def test_null_optional_fields(self, db_conn):
        self._insert_test_game(db_conn)

        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
        )

        r = get_analysis(db_conn, "game-1")[0]
        assert r["eval_before"] is None
        assert r["eval_after"] is None
        assert r["mate_before"] is None
        assert r["mate_after"] is None
        assert r["classification"] is None
        assert r["centipawn_loss"] is None
        assert r["candidate_moves"] == []
        assert r["insight"] is None

    def test_get_analysis_empty(self, db_conn):
        assert get_analysis(db_conn, "no-such-game") == []

    def test_mate_values_stored(self, db_conn):
        self._insert_test_game(db_conn)

        insert_analysis_result(
            db_conn, "game-1", move_index=0, is_white=True,
            move_san="e4", fen_before="f0", fen_after="f1",
            mate_before=3, mate_after=None, eval_before=None, eval_after=50,
        )

        r = get_analysis(db_conn, "game-1")[0]
        assert r["mate_before"] == 3
        assert r["mate_after"] is None
        assert r["eval_before"] is None
        assert r["eval_after"] == 50


# ---------------------------------------------------------------------------
# Analysis summary CRUD
# ---------------------------------------------------------------------------


class TestAnalysisSummary:
    def _insert_test_game(self, conn):
        game = ParsedGame(
            event="E", site="S", date="2024.01.01", round="-",
            white="w", black="b", result="1-0",
            moves=["e4"], fens=["fen1"],
        )
        insert_game(conn, "game-1", "user", "pgn", game)

    def test_insert_and_get_summary(
        self, db_conn, sample_white_summary, sample_black_summary
    ):
        self._insert_test_game(db_conn)

        upsert_analysis_summary(
            db_conn, "game-1", is_complete=True,
            white_summary=sample_white_summary,
            black_summary=sample_black_summary,
        )

        summary = get_analysis_summary(db_conn, "game-1")
        assert summary is not None
        assert summary["is_complete"] is True
        assert summary["white_best"] == 5
        assert summary["white_excellent"] == 3
        assert summary["white_good"] == 2
        assert summary["white_inaccuracy"] == 1
        assert summary["white_mistake"] == 0
        assert summary["white_blunder"] == 0
        assert summary["white_final_rating"] == 1540
        assert summary["white_performance_ratings"] == [1500, 1520, 1540]
        assert summary["black_best"] == 4
        assert summary["black_mistake"] == 1
        assert summary["black_blunder"] == 1
        assert summary["black_final_rating"] == 1350
        assert summary["black_performance_ratings"] == [1400, 1380, 1350]

    def test_upsert_updates_existing(
        self, db_conn, sample_white_summary, sample_black_summary
    ):
        self._insert_test_game(db_conn)

        # First insert – incomplete
        upsert_analysis_summary(
            db_conn, "game-1", is_complete=False,
            white_summary=sample_white_summary,
            black_summary=sample_black_summary,
        )
        assert get_analysis_summary(db_conn, "game-1")["is_complete"] is False

        # Update – mark complete with different counts
        updated_white = PlayerAnalysisSummary(
            best_count=10, excellent_count=5, good_count=4,
            inaccuracy_count=2, mistake_count=1, blunder_count=0,
            performance_ratings=[1500, 1550, 1600],
            final_performance_rating=1600,
        )
        upsert_analysis_summary(
            db_conn, "game-1", is_complete=True,
            white_summary=updated_white,
            black_summary=sample_black_summary,
        )

        summary = get_analysis_summary(db_conn, "game-1")
        assert summary["is_complete"] is True
        assert summary["white_best"] == 10
        assert summary["white_final_rating"] == 1600

    def test_get_nonexistent_summary(self, db_conn):
        assert get_analysis_summary(db_conn, "no-such-game") is None


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------


class TestRetryBehavior:
    def test_retry_decorator_retries_once(self):
        """Verify _with_retry calls the function a second time on failure."""
        from app.database import _with_retry

        call_count = 0

        @_with_retry
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = flaky_operation()
        assert result == "success"
        assert call_count == 2

    def test_retry_decorator_propagates_on_second_failure(self):
        """If both attempts fail, the error propagates."""
        from app.database import _with_retry

        @_with_retry
        def always_fails():
            raise sqlite3.OperationalError("database is locked")

        with pytest.raises(sqlite3.OperationalError):
            always_fails()

    def test_retry_decorator_no_retry_on_success(self):
        """A successful first call should not trigger a retry."""
        from app.database import _with_retry

        call_count = 0

        @_with_retry
        def succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeeds()
        assert result == "ok"
        assert call_count == 1
