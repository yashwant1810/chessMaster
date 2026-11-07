"""Property-based tests for username validation.

Feature: chess-review-engine, Property 5: Username validation rejects invalid input

**Validates: Requirements 1.6**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.validators import MAX_USERNAME_LENGTH, validate_username


@settings(max_examples=100)
@given(username=st.text(min_size=1, max_size=MAX_USERNAME_LENGTH))
def test_valid_usernames_accepted(username: str) -> None:
    """Non-empty strings of at most 25 characters are accepted.

    **Validates: Requirements 1.6**
    """
    result = validate_username(username)
    assert result.is_valid is True, (
        f"Expected valid for username of length {len(username)!r}, got error: {result.error_message}"
    )
    assert result.error_code is None
    assert result.error_message is None


@settings(max_examples=100)
@given(username=st.text(min_size=MAX_USERNAME_LENGTH + 1, max_size=100))
def test_too_long_usernames_rejected(username: str) -> None:
    """Strings exceeding 25 characters are rejected.

    **Validates: Requirements 1.6**
    """
    result = validate_username(username)
    assert result.is_valid is False, (
        f"Expected rejection for username of length {len(username)}"
    )
    assert result.error_code == "invalid_username"
    assert result.error_message is not None


def test_empty_username_rejected() -> None:
    """Empty string is rejected.

    **Validates: Requirements 1.6**
    """
    result = validate_username("")
    assert result.is_valid is False
    assert result.error_code == "invalid_username"
    assert result.error_message is not None
