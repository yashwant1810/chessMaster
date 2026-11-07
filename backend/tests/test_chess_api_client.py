"""Unit tests for the chess.com API client."""

import httpx
import pytest

from app.services.chess_api_client import (
    BASE_URL,
    ChessComAPIClient,
    ChessComAPIError,
    ConnectionFailedError,
    GameNotFoundError,
    UsernameNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_transport():
    """Create a callable mock transport for httpx."""
    class _MockTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.responses: dict[str, httpx.Response] = {}
            self.side_effects: dict[str, Exception] = {}

        def add_response(self, path: str, *, status_code: int = 200, json_data: dict | list | None = None):
            body = httpx.Response(status_code, json=json_data or {})
            self.responses[path] = body

        def add_error(self, path: str, error: Exception):
            self.side_effects[path] = error

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            path = str(request.url)
            # Check for side effects first
            for key, exc in self.side_effects.items():
                if key in path:
                    raise exc
            # Check for registered responses
            for key, resp in self.responses.items():
                if key in path:
                    return resp
            # Default: 404
            return httpx.Response(404, json={"message": "Not found"})

    return _MockTransport()


@pytest.fixture
def client(mock_transport):
    """Create a ChessComAPIClient backed by the mock transport."""
    api_client = ChessComAPIClient()
    api_client._client = httpx.AsyncClient(
        transport=mock_transport,
        base_url=BASE_URL,
        timeout=httpx.Timeout(30.0),
    )
    return api_client, mock_transport


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify custom exception structure."""

    def test_username_not_found_is_chess_api_error(self):
        exc = UsernameNotFoundError("testuser")
        assert isinstance(exc, ChessComAPIError)
        assert "testuser" in str(exc)
        assert exc.username == "testuser"

    def test_game_not_found_is_chess_api_error(self):
        exc = GameNotFoundError("https://chess.com/game/live/123")
        assert isinstance(exc, ChessComAPIError)
        assert "123" in str(exc)
        assert exc.identifier == "https://chess.com/game/live/123"

    def test_connection_failed_is_chess_api_error(self):
        exc = ConnectionFailedError()
        assert isinstance(exc, ChessComAPIError)
        assert "Connection to chess.com failed" in str(exc)

    def test_connection_failed_custom_reason(self):
        exc = ConnectionFailedError("Timeout after 30s")
        assert "Timeout after 30s" in str(exc)


# ---------------------------------------------------------------------------
# get_player_archives
# ---------------------------------------------------------------------------


class TestGetPlayerArchives:
    """Tests for ChessComAPIClient.get_player_archives."""

    @pytest.mark.asyncio
    async def test_returns_archive_urls(self, client):
        api_client, transport = client
        archives = [
            "https://api.chess.com/pub/player/hikaru/games/2024/01",
            "https://api.chess.com/pub/player/hikaru/games/2024/02",
        ]
        transport.add_response(
            "/pub/player/hikaru/games/archives",
            json_data={"archives": archives},
        )

        result = await api_client.get_player_archives("hikaru")
        assert result == archives

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_archives(self, client):
        api_client, transport = client
        transport.add_response(
            "/pub/player/newplayer/games/archives",
            json_data={"archives": []},
        )

        result = await api_client.get_player_archives("newplayer")
        assert result == []

    @pytest.mark.asyncio
    async def test_raises_username_not_found_on_404(self, client):
        api_client, transport = client
        transport.add_response(
            "/pub/player/nonexistent/games/archives",
            status_code=404,
            json_data={"message": "Not found"},
        )

        with pytest.raises(UsernameNotFoundError) as exc_info:
            await api_client.get_player_archives("nonexistent")
        assert exc_info.value.username == "nonexistent"

    @pytest.mark.asyncio
    async def test_raises_connection_failed_on_timeout(self, client):
        api_client, transport = client
        transport.add_error(
            "/pub/player/hikaru/games/archives",
            httpx.ReadTimeout("timed out"),
        )

        with pytest.raises(ConnectionFailedError):
            await api_client.get_player_archives("hikaru")

    @pytest.mark.asyncio
    async def test_raises_connection_failed_on_network_error(self, client):
        api_client, transport = client
        transport.add_error(
            "/pub/player/hikaru/games/archives",
            httpx.ConnectError("connection refused"),
        )

        with pytest.raises(ConnectionFailedError):
            await api_client.get_player_archives("hikaru")


# ---------------------------------------------------------------------------
# get_monthly_games
# ---------------------------------------------------------------------------


class TestGetMonthlyGames:
    """Tests for ChessComAPIClient.get_monthly_games."""

    @pytest.mark.asyncio
    async def test_returns_games_list(self, client):
        api_client, transport = client
        games = [
            {"pgn": "[Event \"Live\"]\n1. e4 e5 *", "url": "https://chess.com/game/live/1"},
            {"pgn": "[Event \"Live\"]\n1. d4 d5 *", "url": "https://chess.com/game/live/2"},
        ]
        transport.add_response(
            "/pub/player/hikaru/games/2024/01",
            json_data={"games": games},
        )

        result = await api_client.get_monthly_games(
            "https://api.chess.com/pub/player/hikaru/games/2024/01"
        )
        assert len(result) == 2
        assert result[0]["pgn"] == games[0]["pgn"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_games(self, client):
        api_client, transport = client
        transport.add_response(
            "/pub/player/hikaru/games/2024/06",
            json_data={"games": []},
        )

        result = await api_client.get_monthly_games(
            "https://api.chess.com/pub/player/hikaru/games/2024/06"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_raises_game_not_found_on_404(self, client):
        api_client, transport = client
        archive_url = "https://api.chess.com/pub/player/hikaru/games/1990/01"
        transport.add_response(
            "/pub/player/hikaru/games/1990/01",
            status_code=404,
        )

        with pytest.raises(GameNotFoundError):
            await api_client.get_monthly_games(archive_url)

    @pytest.mark.asyncio
    async def test_raises_connection_failed_on_timeout(self, client):
        api_client, transport = client
        transport.add_error(
            "/pub/player/hikaru/games/2024/01",
            httpx.ReadTimeout("timed out"),
        )

        with pytest.raises(ConnectionFailedError):
            await api_client.get_monthly_games(
                "https://api.chess.com/pub/player/hikaru/games/2024/01"
            )


# ---------------------------------------------------------------------------
# get_game_by_url
# ---------------------------------------------------------------------------


class TestGetGameByUrl:
    """Tests for ChessComAPIClient.get_game_by_url."""

    @pytest.mark.asyncio
    async def test_fetches_live_game(self, client):
        api_client, transport = client
        game_data = {"pgn": "[Event \"Live\"]\n1. e4 e5 *", "url": "https://chess.com/game/live/12345"}
        transport.add_response(
            "/pub/game/live/12345",
            json_data=game_data,
        )

        result = await api_client.get_game_by_url("https://www.chess.com/game/live/12345")
        assert result["pgn"] == game_data["pgn"]

    @pytest.mark.asyncio
    async def test_fetches_daily_game_after_live_404(self, client):
        api_client, transport = client
        game_data = {"pgn": "[Event \"Daily\"]\n1. d4 d5 *"}
        transport.add_response(
            "/pub/game/live/99999",
            status_code=404,
        )
        transport.add_response(
            "/pub/game/daily/99999",
            json_data=game_data,
        )

        result = await api_client.get_game_by_url("https://www.chess.com/game/daily/99999")
        assert result["pgn"] == game_data["pgn"]

    @pytest.mark.asyncio
    async def test_raises_game_not_found_when_neither_live_nor_daily(self, client):
        api_client, transport = client
        transport.add_response("/pub/game/live/11111", status_code=404)
        transport.add_response("/pub/game/daily/11111", status_code=404)

        with pytest.raises(GameNotFoundError):
            await api_client.get_game_by_url("https://www.chess.com/game/live/11111")

    @pytest.mark.asyncio
    async def test_raises_game_not_found_for_invalid_url_format(self, client):
        api_client, _ = client

        with pytest.raises(GameNotFoundError):
            await api_client.get_game_by_url("https://example.com/not-a-chess-url")

    @pytest.mark.asyncio
    async def test_raises_connection_failed_on_network_error(self, client):
        api_client, transport = client
        transport.add_error(
            "/pub/game/live/12345",
            httpx.ConnectError("connection refused"),
        )

        with pytest.raises(ConnectionFailedError):
            await api_client.get_game_by_url("https://www.chess.com/game/live/12345")

    @pytest.mark.asyncio
    async def test_raises_connection_failed_on_unexpected_status(self, client):
        api_client, transport = client
        transport.add_response("/pub/game/live/12345", status_code=500)

        with pytest.raises(ConnectionFailedError):
            await api_client.get_game_by_url("https://www.chess.com/game/live/12345")


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    """Verify async context manager protocol."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with ChessComAPIClient() as api_client:
            assert api_client._client is not None
        # After exiting, the client should be closed
        assert api_client._client.is_closed
