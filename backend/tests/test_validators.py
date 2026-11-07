"""Unit tests for username and game URL validators."""

from app.services.validators import (
    MAX_USERNAME_LENGTH,
    ValidationResult,
    validate_game_url,
    validate_username,
)


# ---------------------------------------------------------------------------
# validate_username
# ---------------------------------------------------------------------------


class TestValidateUsername:
    """Tests for validate_username."""

    def test_valid_short_username(self) -> None:
        result = validate_username("alice")
        assert result.is_valid is True
        assert result.error_code is None
        assert result.error_message is None

    def test_valid_single_char(self) -> None:
        result = validate_username("a")
        assert result.is_valid is True

    def test_valid_exactly_25_chars(self) -> None:
        username = "a" * MAX_USERNAME_LENGTH
        result = validate_username(username)
        assert result.is_valid is True

    def test_reject_empty_string(self) -> None:
        result = validate_username("")
        assert result.is_valid is False
        assert result.error_code == "invalid_username"
        assert result.error_message is not None

    def test_reject_exceeds_25_chars(self) -> None:
        username = "a" * (MAX_USERNAME_LENGTH + 1)
        result = validate_username(username)
        assert result.is_valid is False
        assert result.error_code == "invalid_username"

    def test_valid_username_with_numbers(self) -> None:
        result = validate_username("player123")
        assert result.is_valid is True

    def test_valid_username_with_special_chars(self) -> None:
        result = validate_username("player_one-2")
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_game_url
# ---------------------------------------------------------------------------


class TestValidateGameUrl:
    """Tests for validate_game_url."""

    def test_valid_live_game_url(self) -> None:
        result = validate_game_url("https://www.chess.com/game/live/12345678")
        assert result.is_valid is True

    def test_valid_daily_game_url(self) -> None:
        result = validate_game_url("https://www.chess.com/game/daily/99999999")
        assert result.is_valid is True

    def test_valid_without_www(self) -> None:
        result = validate_game_url("https://chess.com/game/live/12345678")
        assert result.is_valid is True

    def test_valid_http_scheme(self) -> None:
        result = validate_game_url("http://www.chess.com/game/live/12345678")
        assert result.is_valid is True

    def test_reject_empty_string(self) -> None:
        result = validate_game_url("")
        assert result.is_valid is False
        assert result.error_code == "invalid_url"

    def test_reject_random_url(self) -> None:
        result = validate_game_url("https://example.com/game/live/12345678")
        assert result.is_valid is False
        assert result.error_code == "invalid_url"

    def test_reject_missing_game_id(self) -> None:
        result = validate_game_url("https://www.chess.com/game/live/")
        assert result.is_valid is False

    def test_reject_non_numeric_game_id(self) -> None:
        result = validate_game_url("https://www.chess.com/game/live/abcdef")
        assert result.is_valid is False

    def test_reject_unsupported_game_type(self) -> None:
        result = validate_game_url("https://www.chess.com/game/blitz/12345678")
        assert result.is_valid is False

    def test_reject_plain_text(self) -> None:
        result = validate_game_url("not a url at all")
        assert result.is_valid is False
        assert result.error_code == "invalid_url"
        assert result.error_message is not None

    def test_reject_trailing_slash(self) -> None:
        result = validate_game_url("https://www.chess.com/game/live/12345678/")
        assert result.is_valid is False

    def test_reject_extra_path_segments(self) -> None:
        result = validate_game_url(
            "https://www.chess.com/game/live/12345678/extra"
        )
        assert result.is_valid is False
