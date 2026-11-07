"""Input validators for chess.com usernames and game URLs.

Provides structured validation with error codes matching the API error table
defined in the design document.
"""

import re
from dataclasses import dataclass

# Maximum allowed username length per Requirement 1.6
MAX_USERNAME_LENGTH = 25

# Regex for chess.com game URLs
# Matches: https://www.chess.com/game/live/<id> and https://www.chess.com/game/daily/<id>
_CHESS_COM_GAME_URL_PATTERN = re.compile(
    r"^https?://(?:www\.)?chess\.com/game/(?:live|daily)/\d+$"
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of an input validation check.

    Attributes:
        is_valid: Whether the input passed validation.
        error_code: Machine-readable error identifier (None when valid).
        error_message: Human-readable error description (None when valid).
    """

    is_valid: bool
    error_code: str | None = None
    error_message: str | None = None


def validate_username(username: str) -> ValidationResult:
    """Validate a chess.com username.

    Accepts non-empty strings of at most 25 characters.

    Args:
        username: The username string to validate.

    Returns:
        ValidationResult indicating whether the username is valid.
        On failure, error_code is ``"invalid_username"`` and
        error_message describes the constraint that was violated.
    """
    if not username:
        return ValidationResult(
            is_valid=False,
            error_code="invalid_username",
            error_message="Username must be 1-25 characters",
        )

    if len(username) > MAX_USERNAME_LENGTH:
        return ValidationResult(
            is_valid=False,
            error_code="invalid_username",
            error_message="Username must be 1-25 characters",
        )

    return ValidationResult(is_valid=True)


def validate_game_url(url: str) -> ValidationResult:
    """Validate a chess.com game URL.

    Accepts URLs matching the pattern:
        ``https://www.chess.com/game/{live|daily}/{numeric_id}``

    The scheme may be ``http`` or ``https`` and the ``www.`` prefix is optional.

    Args:
        url: The URL string to validate.

    Returns:
        ValidationResult indicating whether the URL is a valid chess.com game URL.
        On failure, error_code is ``"invalid_url"`` and error_message describes
        the expected format.
    """
    if _CHESS_COM_GAME_URL_PATTERN.match(url):
        return ValidationResult(is_valid=True)

    return ValidationResult(
        is_valid=False,
        error_code="invalid_url",
        error_message="Not a valid chess.com game URL",
    )
