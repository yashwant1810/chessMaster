"""Unit tests for the Game Fetcher service.

Tests fetch_profile_games and fetch_game_by_url with mocked chess.com API
responses, validators, PGN parser, and database layer.

Requirements tested: 1.1, 1.5, 1.6, 1.7, 1.8, 2.1, 2.4, 2.5, 2.7
"""

import sqlite3
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import FetchResult, ParsedGame
from app.services.chess_api_client import (
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)
from app.services.game_fetcher import GameFetcher
from app.services.pgn_parser import PGNParseError
from app.services.validators import ValidationResult


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

VALID = ValidationResult(is_valid=True)
INVALID_USERNAME = ValidationResult(
    is_valid=False,
    error_code="invalid_username",
    error_message="Username must be 1-25 characters",
)
INVALID_URL = ValidationResult(
    is_valid=False,
    error_code="invalid_url",
    error_message="Not a valid chess.com game URL",
)

SAMPLE_PGN = '[Event "Live"]\n[White "p1"]\n[Black "p2"]\n[Result "1-0"]\n\n1. e4 e5 1-0'


def _parsed_game(**overrides) -> ParsedGame:
    """Return a ParsedGame with sensible defaults."""
    defaults = dict(
        event="Live Chess",
        site="chess.com",
        date="2024.01.15",
        round="-",
        white="player1",
        black="player2",
        result="1-0",
        moves=["e4", "e5", "Nf3"],
        fens=["fen1", "fen2", "fen3"],
    )
    defaults.update(overrides)
    return ParsedGame(**defaults)


def _game_data(game_id: int = 1) -> dict:
    """Return a game dict mimicking the chess.com monthly-games response."""
    return {
        "url": f"https://www.chess.com/game/live/{game_id}",
        "pgn": SAMPLE_PGN,
        "time_control": "600",
        "white": {"username": "player1"},
        "black": {"username": "player2"},
    }


def _game_data_list(count: int, start_id: int = 1) -> list[dict]:
    """Return *count* game-data dicts with sequential IDs."""
    return [_game_data(game_id=start_id + i) for i in range(count)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api():
    """AsyncMock standing in for ChessComAPIClient."""
    return AsyncMock()


@pytest.fixture
def db():
    """MagicMock standing in for sqlite3.Connection."""
    return MagicMock(spec=sqlite3.Connection)


@pytest.fixture
def fetcher(api, db):
    """GameFetcher wired to mocked API client and DB connection."""
    return GameFetcher(api_client=api, db_conn=db)


@pytest.fixture
def mocks(monkeypatch):
    """Patch module-level imports in game_fetcher; return a dict of mocks.

    Defaults:
      - validate_username → VALID
      - validate_game_url → VALID
      - parse_pgn → a default ParsedGame
      - insert_game → "test-game-id"
    """
    m_validate_user = MagicMock(return_value=VALID)
    m_validate_url = MagicMock(return_value=VALID)
    m_parse_pgn = MagicMock(return_value=_parsed_game())
    m_insert_game = MagicMock(return_value="test-game-id")

    monkeypatch.setattr(
        "app.services.game_fetcher.validate_username", m_validate_user
    )
    monkeypatch.setattr(
        "app.services.game_fetcher.validate_game_url", m_validate_url
    )
    monkeypatch.setattr("app.services.game_fetcher.parse_pgn", m_parse_pgn)
    monkeypatch.setattr("app.services.game_fetcher.insert_game", m_insert_game)

    return {
        "validate_username": m_validate_user,
        "validate_game_url": m_validate_url,
        "parse_pgn": m_parse_pgn,
        "insert_game": m_insert_game,
    }


# ---------------------------------------------------------------------------
# fetch_profile_games
# ---------------------------------------------------------------------------


class TestFetchProfileGames:
    """Tests for GameFetcher.fetch_profile_games."""

    @pytest.mark.asyncio
    async def test_fetches_games_from_multiple_archives(self, fetcher, api, mocks):
        """Req 1.1: Games across multiple monthly archives are fetched."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
        ]
        api.get_monthly_games.side_effect = [
            _game_data_list(2, start_id=1),  # Feb (most recent, processed first)
            _game_data_list(3, start_id=10),  # Jan
        ]

        result = await fetcher.fetch_profile_games("hikaru")

        assert isinstance(result, FetchResult)
        assert result.games_fetched == 5
        assert result.is_capped is False
        assert result.username == "hikaru"
        assert api.get_monthly_games.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_archives_returns_no_games(self, fetcher, api, mocks):
        """Req 1.7: Username exists but has zero game archives."""
        api.get_player_archives.return_value = []

        result = await fetcher.fetch_profile_games("newplayer")

        assert result.games_fetched == 0
        assert result.is_capped is False
        assert "No games found" in (result.message or "")

    @pytest.mark.asyncio
    async def test_archives_exist_but_all_months_empty(self, fetcher, api, mocks):
        """Req 1.7: Archives exist but contain no games."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
        ]
        api.get_monthly_games.return_value = []

        result = await fetcher.fetch_profile_games("hikaru")

        assert result.games_fetched == 0
        assert "No games found" in (result.message or "")

    @pytest.mark.asyncio
    async def test_invalid_username_raises_value_error(self, fetcher, mocks):
        """Req 1.6: Validation failure raises ValueError."""
        mocks["validate_username"].return_value = INVALID_USERNAME

        with pytest.raises(ValueError, match="Username must be 1-25 characters"):
            await fetcher.fetch_profile_games("")

    @pytest.mark.asyncio
    async def test_username_not_found_on_chess_com(self, fetcher, api, mocks):
        """Req 1.8: chess.com 404 propagates UsernameNotFoundError."""
        api.get_player_archives.side_effect = UsernameNotFoundError("ghost")

        with pytest.raises(UsernameNotFoundError):
            await fetcher.fetch_profile_games("ghost")

    @pytest.mark.asyncio
    async def test_connection_timeout_propagates(self, fetcher, api, mocks):
        """Req 1.5: Network timeout propagates ConnectionFailedError."""
        api.get_player_archives.side_effect = ConnectionFailedError(
            "Connection to chess.com failed"
        )

        with pytest.raises(ConnectionFailedError):
            await fetcher.fetch_profile_games("hikaru")

    @pytest.mark.asyncio
    async def test_progress_callback_invoked_per_archive(self, fetcher, api, mocks):
        """Progress callback receives (index, total) after each archive."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
            "https://api.chess.com/pub/player/hikaru/games/2024/03",
        ]
        api.get_monthly_games.side_effect = [
            _game_data_list(1, start_id=1),
            _game_data_list(1, start_id=10),
            _game_data_list(1, start_id=20),
        ]

        callback = MagicMock()
        await fetcher.fetch_profile_games("hikaru", progress_callback=callback)

        assert callback.call_count == 3
        callback.assert_any_call(1, 3)
        callback.assert_any_call(2, 3)
        callback.assert_any_call(3, 3)

    @pytest.mark.asyncio
    async def test_game_cap_stops_fetching(self, fetcher, api, mocks, monkeypatch):
        """Req 1.1: Fetching stops at the MAX_GAMES cap and flags is_capped."""
        monkeypatch.setattr("app.services.game_fetcher.MAX_GAMES", 5)

        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
        ]
        api.get_monthly_games.side_effect = [
            _game_data_list(4, start_id=1),  # Feb: 4 games
            _game_data_list(4, start_id=10),  # Jan: only 1 more needed
        ]

        result = await fetcher.fetch_profile_games("hikaru")

        assert result.games_fetched == 5
        assert result.is_capped is True

    @pytest.mark.asyncio
    async def test_pgn_parse_failure_skips_game(self, fetcher, api, mocks):
        """Failed PGN parse for one game skips it; other games still fetched."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
        ]
        api.get_monthly_games.return_value = _game_data_list(3, start_id=1)

        mocks["parse_pgn"].side_effect = [
            _parsed_game(),
            PGNParseError("bad move", location="move 5"),
            _parsed_game(),
        ]

        result = await fetcher.fetch_profile_games("hikaru")

        assert result.games_fetched == 2

    @pytest.mark.asyncio
    async def test_games_without_pgn_skipped(self, fetcher, api, mocks):
        """Games missing a PGN field are silently skipped."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
        ]
        api.get_monthly_games.return_value = [
            _game_data(1),
            {"url": "https://www.chess.com/game/live/2"},  # no pgn
            _game_data(3),
        ]

        result = await fetcher.fetch_profile_games("hikaru")

        assert result.games_fetched == 2

    @pytest.mark.asyncio
    async def test_empty_archives_callback_receives_zeros(self, fetcher, api, mocks):
        """Progress callback receives (0, 0) when no archives exist."""
        api.get_player_archives.return_value = []
        callback = MagicMock()

        await fetcher.fetch_profile_games("newplayer", progress_callback=callback)

        callback.assert_called_once_with(0, 0)

    @pytest.mark.asyncio
    async def test_archive_fetch_failure_skips_to_next(self, fetcher, api, mocks):
        """Failed archive fetch is skipped; subsequent archives still processed."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
        ]
        api.get_monthly_games.side_effect = [
            ConnectionFailedError("timeout"),  # Feb fails
            _game_data_list(2, start_id=1),  # Jan succeeds
        ]

        callback = MagicMock()
        result = await fetcher.fetch_profile_games(
            "hikaru", progress_callback=callback
        )

        assert result.games_fetched == 2
        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_duplicate_game_still_counted(self, fetcher, api, mocks):
        """IntegrityError on insert (duplicate) still counts the game."""
        api.get_player_archives.return_value = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
        ]
        api.get_monthly_games.return_value = _game_data_list(2, start_id=1)
        mocks["insert_game"].side_effect = sqlite3.IntegrityError("UNIQUE")

        result = await fetcher.fetch_profile_games("hikaru")

        assert result.games_fetched == 2


# ---------------------------------------------------------------------------
# fetch_game_by_url
# ---------------------------------------------------------------------------


class TestFetchGameByUrl:
    """Tests for GameFetcher.fetch_game_by_url."""

    @pytest.mark.asyncio
    async def test_valid_url_fetches_and_stores_game(self, fetcher, api, mocks):
        """Req 2.1, 2.6: Valid URL → game fetched, parsed, stored, confirmed."""
        url = "https://www.chess.com/game/live/12345"
        api.get_game_by_url.return_value = {
            "pgn": SAMPLE_PGN,
            "time_control": "600",
            "white": {"username": "alice"},
            "black": {"username": "bob"},
        }

        result = await fetcher.fetch_game_by_url(url)

        assert result.games_fetched == 1
        assert result.is_capped is False
        assert "available for analysis" in (result.message or "")
        mocks["parse_pgn"].assert_called_once_with(SAMPLE_PGN)
        mocks["insert_game"].assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_url_raises_value_error(self, fetcher, mocks):
        """Req 2.3: Invalid URL format → ValueError."""
        mocks["validate_game_url"].return_value = INVALID_URL

        with pytest.raises(ValueError, match="Not a valid chess.com game URL"):
            await fetcher.fetch_game_by_url("https://example.com/nope")

    @pytest.mark.asyncio
    async def test_game_not_found_propagates(self, fetcher, api, mocks):
        """Req 2.4: chess.com 404 → GameNotFoundError."""
        url = "https://www.chess.com/game/live/99999"
        api.get_game_by_url.side_effect = GameNotFoundError(url)

        with pytest.raises(GameNotFoundError):
            await fetcher.fetch_game_by_url(url)

    @pytest.mark.asyncio
    async def test_connection_failure_propagates(self, fetcher, api, mocks):
        """Req 2.5: Unreachable chess.com → ConnectionFailedError."""
        api.get_game_by_url.side_effect = ConnectionFailedError()

        with pytest.raises(ConnectionFailedError):
            await fetcher.fetch_game_by_url(
                "https://www.chess.com/game/live/12345"
            )

    @pytest.mark.asyncio
    async def test_pgn_parse_failure_raises(self, fetcher, api, mocks):
        """Req 2.7: Successful fetch + PGN parse failure → PGNParseError."""
        api.get_game_by_url.return_value = {
            "pgn": "bad pgn",
            "time_control": "600",
        }
        mocks["parse_pgn"].side_effect = PGNParseError(
            "Invalid move at move 3", location="move 3"
        )

        with pytest.raises(PGNParseError):
            await fetcher.fetch_game_by_url(
                "https://www.chess.com/game/live/12345"
            )

    @pytest.mark.asyncio
    async def test_missing_pgn_in_response_raises_parse_error(self, fetcher, api, mocks):
        """Req 2.7: No PGN data in API response → PGNParseError."""
        api.get_game_by_url.return_value = {"time_control": "600"}

        with pytest.raises(PGNParseError, match="No PGN data"):
            await fetcher.fetch_game_by_url(
                "https://www.chess.com/game/live/12345"
            )

    @pytest.mark.asyncio
    async def test_duplicate_game_returns_success(self, fetcher, api, mocks):
        """Re-fetching an existing game (IntegrityError) still returns success."""
        api.get_game_by_url.return_value = {
            "pgn": SAMPLE_PGN,
            "time_control": "600",
            "white": {"username": "alice"},
        }
        mocks["insert_game"].side_effect = sqlite3.IntegrityError("UNIQUE")

        result = await fetcher.fetch_game_by_url(
            "https://www.chess.com/game/live/12345"
        )

        assert result.games_fetched == 1
        assert "available for analysis" in (result.message or "")

    @pytest.mark.asyncio
    async def test_username_derived_from_parsed_game_when_absent(
        self, fetcher, api, mocks
    ):
        """Username falls back to ParsedGame.white when absent from API response."""
        mocks["parse_pgn"].return_value = _parsed_game(white="fallback_user")
        api.get_game_by_url.return_value = {
            "pgn": SAMPLE_PGN,
            "time_control": "600",
        }

        result = await fetcher.fetch_game_by_url(
            "https://www.chess.com/game/live/12345"
        )

        assert result.username == "fallback_user"
