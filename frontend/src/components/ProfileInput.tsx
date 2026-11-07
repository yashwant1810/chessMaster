/**
 * ProfileInput — accepts a chess.com username or game URL and fetches data.
 *
 * Auto-detects whether the input is a URL (starts with "http") or a username.
 * Validates the input client-side before making the API call:
 * - Username: non-empty, max 25 characters
 * - Game URL: must match chess.com game URL pattern
 *
 * On success: updates app context (username + games) and remains on the home page
 * where the GameList component (added in task 8.4) will render.
 *
 * Requirements: 1.6, 2.3, 2.6
 */

import { type FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAppContext } from "../context/AppContext";

/** Maximum allowed username length per Requirement 1.6. */
const MAX_USERNAME_LENGTH = 25;

/**
 * Regex matching chess.com game URLs.
 * Accepts: https://www.chess.com/game/live/<id> and https://www.chess.com/game/daily/<id>
 * The `www.` prefix is optional.
 */
const CHESS_COM_GAME_URL_PATTERN =
  /^https?:\/\/(?:www\.)?chess\.com\/game\/(?:live|daily)\/\d+$/;

/** Determine whether the user input looks like a URL. */
export function isUrlInput(value: string): boolean {
  return value.startsWith("http://") || value.startsWith("https://");
}

/**
 * Validate a chess.com username on the client side.
 *
 * @returns An error message string, or `null` if valid.
 */
export function validateUsername(username: string): string | null {
  const trimmed = username.trim();
  if (trimmed.length === 0) {
    return "Username cannot be empty";
  }
  if (trimmed.length > MAX_USERNAME_LENGTH) {
    return `Username must be at most ${MAX_USERNAME_LENGTH} characters`;
  }
  return null;
}

/**
 * Validate a chess.com game URL on the client side.
 *
 * @returns An error message string, or `null` if valid.
 */
export function validateGameUrl(url: string): string | null {
  const trimmed = url.trim();
  if (trimmed.length === 0) {
    return "URL cannot be empty";
  }
  if (!CHESS_COM_GAME_URL_PATTERN.test(trimmed)) {
    return "Not a valid chess.com game URL";
  }
  return null;
}

export default function ProfileInput() {
  const { setUsername, setGames } = useAppContext();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmed = input.trim();
    const isUrl = isUrlInput(trimmed);

    // Client-side validation
    const validationError = isUrl
      ? validateGameUrl(trimmed)
      : validateUsername(trimmed);

    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    try {
      if (isUrl) {
        await api.fetchGameByUrl(trimmed);
      } else {
        await api.fetchProfile(trimmed);
      }

      // On success: fetch the game list and update context
      const games = await api.getGames();

      if (!isUrl) {
        setUsername(trimmed);
      }
      setGames(games);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="profile-input"
      aria-label="Load chess.com games"
    >
      <div className="profile-input__field">
        <label htmlFor="profile-input-field">
          Chess.com username or game URL
        </label>
        <input
          id="profile-input-field"
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            if (error) setError(null);
          }}
          placeholder="e.g. magnus or https://www.chess.com/game/live/12345"
          disabled={loading}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? "profile-input-error" : undefined}
        />
      </div>

      {error && (
        <p
          id="profile-input-error"
          className="profile-input__error"
          role="alert"
        >
          {error}
        </p>
      )}

      <button type="submit" disabled={loading}>
        {loading ? (
          <span className="profile-input__loading" aria-label="Loading">
            Loading…
          </span>
        ) : (
          "Load Games"
        )}
      </button>
    </form>
  );
}
