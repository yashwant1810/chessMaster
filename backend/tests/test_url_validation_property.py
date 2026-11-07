"""Property-based tests for chess.com game URL validation.

Feature: chess-review-engine, Property 6: URL validation rejects invalid format

**Validates: Requirements 2.3**
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.services.validators import validate_game_url


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid chess.com game URL components
_SCHEMES = st.sampled_from(["http", "https"])
_WWW_PREFIX = st.sampled_from(["www.", ""])
_GAME_TYPES = st.sampled_from(["live", "daily"])
_GAME_IDS = st.integers(min_value=1, max_value=10**15).map(str)


@st.composite
def valid_chess_com_urls(draw: st.DrawFn) -> str:
    """Generate valid chess.com game URLs that should be accepted."""
    scheme = draw(_SCHEMES)
    www = draw(_WWW_PREFIX)
    game_type = draw(_GAME_TYPES)
    game_id = draw(_GAME_IDS)
    return f"{scheme}://{www}chess.com/game/{game_type}/{game_id}"


@st.composite
def urls_from_other_domains(draw: st.DrawFn) -> str:
    """Generate URLs from domains that are not chess.com."""
    domains = st.sampled_from([
        "example.com",
        "lichess.org",
        "chess24.com",
        "google.com",
        "chesscom.com",
        "notchess.com",
        "chess.org",
        "chess.net",
    ])
    scheme = draw(_SCHEMES)
    domain = draw(domains)
    game_type = draw(_GAME_TYPES)
    game_id = draw(_GAME_IDS)
    return f"{scheme}://{domain}/game/{game_type}/{game_id}"


@st.composite
def chess_com_urls_wrong_path(draw: st.DrawFn) -> str:
    """Generate chess.com URLs with incorrect path structures."""
    scheme = draw(_SCHEMES)
    www = draw(_WWW_PREFIX)
    wrong_paths = st.sampled_from([
        # Wrong game type
        "/game/blitz/12345",
        "/game/bullet/12345",
        "/game/rapid/12345",
        "/game/correspondence/12345",
        # Missing game type
        "/game/12345",
        # Wrong base path
        "/games/live/12345",
        "/match/live/12345",
        "/play/live/12345",
        # Non-numeric game id
        "/game/live/abcdef",
        "/game/daily/xyz",
        "/game/live/123abc",
        # Missing game id
        "/game/live/",
        "/game/daily/",
        "/game/live",
        "/game/daily",
        # Extra path segments
        "/game/live/12345/extra",
        "/game/daily/12345/more/stuff",
        # Trailing slash
        "/game/live/12345/",
        # Completely wrong paths
        "/profile/hikaru",
        "/member/hikaru",
        "/analysis",
        "/",
        "",
    ])
    path = draw(wrong_paths)
    return f"{scheme}://{www}chess.com{path}"


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


class TestUrlValidationProperty:
    """Property 6: URL Validation Rejects Invalid Format."""

    @given(url=st.text())
    @settings(max_examples=100)
    def test_random_strings_rejected(self, url: str) -> None:
        """Completely random strings that don't match the pattern are rejected.

        **Validates: Requirements 2.3**
        """
        # Skip strings that accidentally match the valid URL pattern
        import re
        pattern = r"^https?://(?:www\.)?chess\.com/game/(?:live|daily)/\d+$"
        assume(not re.match(pattern, url))

        result = validate_game_url(url)

        assert result.is_valid is False
        assert result.error_code == "invalid_url"
        assert result.error_message is not None

    @given(url=urls_from_other_domains())
    @settings(max_examples=100)
    def test_other_domains_rejected(self, url: str) -> None:
        """URLs from non-chess.com domains are rejected.

        **Validates: Requirements 2.3**
        """
        result = validate_game_url(url)

        assert result.is_valid is False
        assert result.error_code == "invalid_url"
        assert result.error_message is not None

    @given(url=chess_com_urls_wrong_path())
    @settings(max_examples=100)
    def test_chess_com_wrong_paths_rejected(self, url: str) -> None:
        """chess.com URLs with wrong path structure are rejected.

        **Validates: Requirements 2.3**
        """
        result = validate_game_url(url)

        assert result.is_valid is False
        assert result.error_code == "invalid_url"
        assert result.error_message is not None

    @given(url=valid_chess_com_urls())
    @settings(max_examples=100)
    def test_valid_urls_accepted(self, url: str) -> None:
        """Valid chess.com game URLs are accepted.

        **Validates: Requirements 2.3**
        """
        result = validate_game_url(url)

        assert result.is_valid is True
        assert result.error_code is None
        assert result.error_message is None
