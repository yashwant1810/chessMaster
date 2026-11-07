"""Game Fetcher service for retrieving chess games from chess.com.

Fetches player game archives from the chess.com Published-Data API,
parses each game's PGN, and stores the results in the local database.
Progress is reported via an optional callback for SSE streaming.
"""

import logging
import sqlite3
import uuid
from collections.abc import Callable

from app.database import insert_game
from app.models import FetchResult
from app.services.chess_api_client import ChessComAPIClient
from app.services.pgn_parser import PGNParseError, parse_pgn
from app.services.validators import validate_game_url, validate_username

logger = logging.getLogger(__name__)

# Maximum number of games to fetch per profile (Requirement 1.1)
MAX_GAMES = 10_000

# Type alias for progress callbacks: (archives_processed, total_archives)
ProgressCallback = Callable[[int, int], None]


class GameFetcher:
    """Fetches and parses games from the chess.com Published-Data API.

    Uses :class:`ChessComAPIClient` for HTTP communication, the PGN
    parser for game-data extraction, and the database layer for
    persistence.  Progress can be tracked via an optional callback
    for SSE streaming support.

    Args:
        api_client: An initialised chess.com API client.
        db_conn: An open SQLite connection (schema already initialised).
    """

    def __init__(
        self,
        api_client: ChessComAPIClient,
        db_conn: sqlite3.Connection,
    ) -> None:
        self._api = api_client
        self._db = db_conn

    async def fetch_profile_games(
        self,
        username: str,
        progress_callback: ProgressCallback | None = None,
    ) -> FetchResult:
        """Fetch all games for a chess.com username, up to 10,000 most recent.

        Validates the username, retrieves monthly archives from chess.com,
        processes them from most recent to oldest, parses each game's PGN,
        and stores the results in the local database.

        Args:
            username: Chess.com username to fetch games for.
            progress_callback: Optional callback invoked after each archive
                is processed, receiving ``(archives_processed, total_archives)``.

        Returns:
            A :class:`FetchResult` with the count of games fetched and
            whether the 10,000-game cap was reached.

        Raises:
            ValueError: If the username format is invalid (Requirement 1.6).
            UsernameNotFoundError: If the username does not exist on
                chess.com (Requirement 1.8).
            ConnectionFailedError: On network errors or timeouts
                (Requirement 1.5).
        """
        # --- Validate username format (Requirement 1.6) --------------------
        validation = validate_username(username)
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # --- Fetch archive list (Requirement 1.1) --------------------------
        archives = await self._api.get_player_archives(username)

        # --- Handle empty game history (Requirement 1.7) -------------------
        if not archives:
            if progress_callback:
                progress_callback(0, 0)
            return FetchResult(
                username=username,
                games_fetched=0,
                is_capped=False,
                message="No games found for this username",
            )

        # Process from most recent to oldest (Requirement 1.1)
        archives_reversed = list(reversed(archives))
        total_archives = len(archives_reversed)
        games_fetched = 0

        for archive_index, archive_url in enumerate(archives_reversed):
            if games_fetched >= MAX_GAMES:
                break

            try:
                monthly_games = await self._api.get_monthly_games(archive_url)
            except Exception:
                logger.warning(
                    "Failed to fetch archive %s, skipping",
                    archive_url,
                    exc_info=True,
                )
                if progress_callback:
                    progress_callback(archive_index + 1, total_archives)
                continue

            # Process games within the month (most recent first)
            for game_data in reversed(monthly_games):
                if games_fetched >= MAX_GAMES:
                    break

                pgn_raw = game_data.get("pgn")
                if not pgn_raw:
                    # Skip games without PGN data (e.g., aborted games)
                    continue

                try:
                    parsed_game = parse_pgn(pgn_raw)
                except PGNParseError as exc:
                    logger.warning(
                        "PGN parse error in archive %s: %s",
                        archive_url,
                        exc.message,
                    )
                    continue

                # Deterministic game ID from the chess.com game URL so
                # re-fetching the same profile does not create duplicates.
                game_url = game_data.get("url", "")
                game_id = str(
                    uuid.uuid5(uuid.NAMESPACE_URL, game_url)
                    if game_url
                    else uuid.uuid4()
                )

                # Extract metadata available from the API response
                time_control = game_data.get("time_control")

                try:
                    insert_game(
                        self._db,
                        game_id=game_id,
                        username=username,
                        pgn_raw=pgn_raw,
                        game=parsed_game,
                        time_control=time_control,
                    )
                except sqlite3.IntegrityError:
                    # Game already in DB (deterministic ID collision) — still
                    # counts towards the user-visible total.
                    logger.debug(
                        "Game %s already exists, skipping insert",
                        game_id,
                    )

                games_fetched += 1

            # Report progress after each archive (Requirement 1.9)
            if progress_callback:
                progress_callback(archive_index + 1, total_archives)

        is_capped = games_fetched >= MAX_GAMES

        return FetchResult(
            username=username,
            games_fetched=games_fetched,
            is_capped=is_capped,
            message=(
                None
                if games_fetched > 0
                else "No games found for this username"
            ),
        )

    async def fetch_game_by_url(self, url: str) -> FetchResult:
        """Fetch a single game by its chess.com game URL.

        Validates the URL format, retrieves the game from chess.com,
        parses the PGN, and stores it in the local database.

        Unlike :meth:`fetch_profile_games`, a PGN parse failure here is
        a hard error — per Requirement 2.7, if retrieval succeeds but
        parsing fails, the caller receives a parsing error and **not** a
        success confirmation.

        Args:
            url: A chess.com game URL
                (e.g. ``https://www.chess.com/game/live/12345``).

        Returns:
            A :class:`FetchResult` with ``games_fetched=1`` on success
            and a confirmation message (Requirement 2.6).

        Raises:
            ValueError: If the URL format is invalid (Requirement 2.3).
            GameNotFoundError: If the game does not exist on chess.com
                (Requirement 2.4).
            ConnectionFailedError: If chess.com is unreachable or times
                out (Requirement 2.5).
            PGNParseError: If the retrieved PGN cannot be parsed
                (Requirement 2.7).
        """
        # --- Validate URL format (Requirement 2.3) ---------------------
        validation = validate_game_url(url)
        if not validation.is_valid:
            raise ValueError(validation.error_message)

        # --- Fetch game from chess.com (Reqs 2.1, 2.4, 2.5) -----------
        # GameNotFoundError and ConnectionFailedError propagate to caller.
        game_data = await self._api.get_game_by_url(url)

        pgn_raw = game_data.get("pgn")
        if not pgn_raw:
            raise PGNParseError("No PGN data in game response")

        # --- Parse PGN (Requirements 2.2, 2.7) -------------------------
        # PGNParseError propagates — no success confirmation on failure.
        parsed_game = parse_pgn(pgn_raw)

        # --- Store in database (Requirement 2.2) ------------------------
        # Deterministic game ID from the URL for deduplication.
        game_id = str(uuid.uuid5(uuid.NAMESPACE_URL, url))

        # Derive a username from the game response or parsed PGN.
        username = (
            game_data.get("white", {}).get("username")
            if isinstance(game_data.get("white"), dict)
            else None
        ) or parsed_game.white

        time_control = game_data.get("time_control")

        try:
            insert_game(
                self._db,
                game_id=game_id,
                username=username,
                pgn_raw=pgn_raw,
                game=parsed_game,
                time_control=time_control,
            )
        except sqlite3.IntegrityError:
            # Game already in DB (deterministic ID collision) — still a
            # successful fetch from the user's perspective.
            logger.debug(
                "Game %s already exists, skipping insert",
                game_id,
            )

        # --- Return success confirmation (Requirement 2.6) --------------
        return FetchResult(
            username=username,
            games_fetched=1,
            is_capped=False,
            message="Game loaded and available for analysis",
        )
