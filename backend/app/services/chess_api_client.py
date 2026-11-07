"""Chess.com Published-Data API client.

Wraps httpx.AsyncClient to fetch player archives, monthly game lists,
and individual games from the chess.com public REST API.

Error mapping follows the design document:
  - HTTP 404 → UsernameNotFoundError / GameNotFoundError
  - Network errors and timeouts → ConnectionFailedError
"""

import re

import httpx

# Base URL for the chess.com Published-Data API
BASE_URL = "https://api.chess.com"

# Timeout per request in seconds (Requirement 1.5, design doc error handling)
REQUEST_TIMEOUT = 30.0

# Pattern to extract username/YYYY/MM from a monthly archive URL
_ARCHIVE_URL_PATTERN = re.compile(
    r"^https?://api\.chess\.com/pub/player/[^/]+/games/\d{4}/\d{2}$"
)

# Pattern to extract game ID from a chess.com game URL
_GAME_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?chess\.com/game/(?:live|daily)/(\d+)$"
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ChessComAPIError(Exception):
    """Base exception for chess.com API errors."""

    def __init__(self, message: str = "An error occurred with the chess.com API"):
        self.message = message
        super().__init__(self.message)


class UsernameNotFoundError(ChessComAPIError):
    """Raised when the chess.com API returns 404 for a player lookup."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username '{username}' was not found on chess.com")


class GameNotFoundError(ChessComAPIError):
    """Raised when the chess.com API returns 404 for a game lookup."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Game '{identifier}' was not found on chess.com")


class ConnectionFailedError(ChessComAPIError):
    """Raised on network errors or timeouts communicating with chess.com."""

    def __init__(self, reason: str = "Connection to chess.com failed"):
        super().__init__(reason)


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


class ChessComAPIClient:
    """Async client for the chess.com Published-Data API.

    Uses ``httpx.AsyncClient`` with a 30-second per-request timeout.
    The client can be used as an async context manager::

        async with ChessComAPIClient() as client:
            archives = await client.get_player_archives("hikaru")
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            follow_redirects=True,
            base_url=BASE_URL,
            timeout=httpx.Timeout(REQUEST_TIMEOUT),
            headers={"Accept": "application/json"},
        )

    # -- lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "ChessComAPIClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        await self.close()

    # -- public methods ------------------------------------------------------

    async def get_player_archives(self, username: str) -> list[str]:
        """Fetch the list of monthly archive URLs for a player.

        Args:
            username: Chess.com username.

        Returns:
            List of archive URLs, e.g.
            ``["https://api.chess.com/pub/player/hikaru/games/2024/01", ...]``

        Raises:
            UsernameNotFoundError: If the username does not exist on chess.com.
            ConnectionFailedError: On network errors or timeouts.
        """
        url = f"/pub/player/{username}/games/archives"
        data = await self._get_json(url, not_found_error=UsernameNotFoundError(username))
        archives: list[str] = data.get("archives", [])
        return archives

    async def get_monthly_games(self, archive_url: str) -> list[dict]:
        """Fetch games from a monthly archive endpoint.

        Args:
            archive_url: Full archive URL returned by ``get_player_archives``,
                e.g. ``https://api.chess.com/pub/player/hikaru/games/2024/01``.

        Returns:
            List of game dicts, each containing at least a ``"pgn"`` field.

        Raises:
            GameNotFoundError: If the archive endpoint returns 404.
            ConnectionFailedError: On network errors or timeouts.
        """
        data = await self._get_json(
            archive_url,
            not_found_error=GameNotFoundError(archive_url),
            use_absolute_url=True,
        )
        games: list[dict] = data.get("games", [])
        return games

    async def get_game_by_url(self, url: str) -> dict:
        """Fetch a single game by its chess.com game URL.

        The game URL is expected to match the pattern
        ``https://www.chess.com/game/{live|daily}/{id}``.  The method
        resolves the game by fetching the callback endpoint from the
        chess.com API.

        Args:
            url: A chess.com game URL.

        Returns:
            A single game dict containing at least a ``"pgn"`` field.

        Raises:
            GameNotFoundError: If the game does not exist on chess.com.
            ConnectionFailedError: On network errors or timeouts.
        """
        match = _GAME_URL_PATTERN.match(url)
        if not match:
            raise GameNotFoundError(url)

        game_id = match.group(1)

        # The chess.com PubAPI exposes individual game callbacks.
        # Try /pub/game/live/{id} first, fall back to /pub/game/daily/{id}.
        for game_type in ("live", "daily"):
            api_url = f"/pub/game/{game_type}/{game_id}"
            try:
                data = await self._get_json(
                    api_url, not_found_error=GameNotFoundError(url)
                )
                return data
            except GameNotFoundError:
                continue

        raise GameNotFoundError(url)

    # -- internal helpers ----------------------------------------------------

    async def _get_json(
        self,
        url: str,
        *,
        not_found_error: ChessComAPIError,
        use_absolute_url: bool = False,
    ) -> dict:
        """Perform a GET request and return the parsed JSON body.

        Args:
            url: Relative path (when *use_absolute_url* is ``False``) or
                absolute URL (when ``True``).
            not_found_error: Exception instance to raise on HTTP 404.
            use_absolute_url: If ``True``, *url* is treated as an absolute
                URL and sent directly rather than appended to ``BASE_URL``.

        Raises:
            not_found_error: On HTTP 404 responses.
            ConnectionFailedError: On network errors, timeouts, or
                non-200/404 HTTP status codes.
        """
        try:
            if use_absolute_url:
                response = await self._client.get(url)
            else:
                response = await self._client.get(url)

            if response.status_code == 404:
                raise not_found_error

            if response.status_code != 200:
                raise ConnectionFailedError(
                    f"chess.com API returned unexpected status {response.status_code}"
                )

            return response.json()

        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            raise ConnectionFailedError("Connection to chess.com failed") from exc
        except ChessComAPIError:
            # Re-raise our own exceptions without wrapping
            raise
        except httpx.HTTPError as exc:
            raise ConnectionFailedError("Connection to chess.com failed") from exc
