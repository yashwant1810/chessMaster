/**
 * Unit tests for ProfileInput component.
 *
 * Uses React Testing Library to verify:
 * - Client-side validation for usernames and game URLs
 * - Loading state display during fetch
 * - Inline error messages on API failure
 * - Correct API method selection based on input type
 * - Context updates on success
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppProvider } from "../context/AppContext";
import ProfileInput, {
  isUrlInput,
  validateUsername,
  validateGameUrl,
} from "./ProfileInput";
import { api, ApiError } from "../api/client";
import type { FetchResult, GameSummary } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>(
    "../api/client",
  );
  return {
    ...actual,
    api: {
      fetchProfile: vi.fn(),
      fetchGameByUrl: vi.fn(),
      getGames: vi.fn(),
      startAnalysis: vi.fn(),
      getAnalysisStatus: vi.fn(),
      getAnalysis: vi.fn(),
      streamFetchProgress: vi.fn(),
      streamAnalysisProgress: vi.fn(),
    },
  };
});

const mockApi = api as unknown as {
  fetchProfile: ReturnType<typeof vi.fn>;
  fetchGameByUrl: ReturnType<typeof vi.fn>;
  getGames: ReturnType<typeof vi.fn>;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderProfileInput() {
  return render(
    <MemoryRouter>
      <AppProvider>
        <ProfileInput />
      </AppProvider>
    </MemoryRouter>,
  );
}

const FETCH_RESULT: FetchResult = { games_count: 3, message: "OK" };

const SAMPLE_GAMES: GameSummary[] = [
  {
    game_id: "game-1",
    date_played: "2024-01-15T12:00:00Z",
    opponent: "opponent1",
    result: "win",
    time_control: "600",
    opening_name: "Sicilian",
    is_analyzed: false,
  },
];

// ---------------------------------------------------------------------------
// Pure function tests
// ---------------------------------------------------------------------------

describe("isUrlInput", () => {
  it("returns true for http URLs", () => {
    expect(isUrlInput("http://www.chess.com/game/live/12345")).toBe(true);
  });

  it("returns true for https URLs", () => {
    expect(isUrlInput("https://www.chess.com/game/live/12345")).toBe(true);
  });

  it("returns false for plain usernames", () => {
    expect(isUrlInput("magnus")).toBe(false);
  });

  it("returns false for empty string", () => {
    expect(isUrlInput("")).toBe(false);
  });
});

describe("validateUsername", () => {
  it("returns null for valid usernames", () => {
    expect(validateUsername("hikaru")).toBeNull();
  });

  it("returns null for username at max length (25 chars)", () => {
    expect(validateUsername("a".repeat(25))).toBeNull();
  });

  it("returns error for empty username", () => {
    expect(validateUsername("")).not.toBeNull();
  });

  it("returns error for whitespace-only username", () => {
    expect(validateUsername("   ")).not.toBeNull();
  });

  it("returns error for username exceeding 25 chars", () => {
    expect(validateUsername("a".repeat(26))).not.toBeNull();
  });
});

describe("validateGameUrl", () => {
  it("returns null for valid live game URL", () => {
    expect(
      validateGameUrl("https://www.chess.com/game/live/12345"),
    ).toBeNull();
  });

  it("returns null for valid daily game URL", () => {
    expect(
      validateGameUrl("https://www.chess.com/game/daily/67890"),
    ).toBeNull();
  });

  it("returns null for URL without www prefix", () => {
    expect(
      validateGameUrl("https://chess.com/game/live/12345"),
    ).toBeNull();
  });

  it("returns error for empty string", () => {
    expect(validateGameUrl("")).not.toBeNull();
  });

  it("returns error for non-chess.com URL", () => {
    expect(validateGameUrl("https://example.com/game/12345")).not.toBeNull();
  });

  it("returns error for chess.com URL without game path", () => {
    expect(validateGameUrl("https://www.chess.com/member/hikaru")).not.toBeNull();
  });

  it("returns error for chess.com URL with non-numeric game ID", () => {
    expect(
      validateGameUrl("https://www.chess.com/game/live/abc"),
    ).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Component rendering tests
// ---------------------------------------------------------------------------

describe("ProfileInput component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form with input, label, and submit button", () => {
    renderProfileInput();

    expect(
      screen.getByLabelText(/chess\.com username or game url/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /load games/i }),
    ).toBeInTheDocument();
  });

  it("shows validation error for empty username submission", async () => {
    renderProfileInput();

    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    expect(
      await screen.findByText(/username cannot be empty/i),
    ).toBeInTheDocument();
    expect(mockApi.fetchProfile).not.toHaveBeenCalled();
  });

  it("shows validation error for username exceeding 25 characters", async () => {
    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "a".repeat(26) } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    expect(
      await screen.findByText(/at most 25 characters/i),
    ).toBeInTheDocument();
    expect(mockApi.fetchProfile).not.toHaveBeenCalled();
  });

  it("shows validation error for invalid game URL", async () => {
    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, {
      target: { value: "https://example.com/game/123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    expect(
      await screen.findByText(/not a valid chess\.com game url/i),
    ).toBeInTheDocument();
    expect(mockApi.fetchGameByUrl).not.toHaveBeenCalled();
  });

  it("clears error when user modifies input", async () => {
    renderProfileInput();

    // Trigger an error first
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));
    expect(
      await screen.findByText(/username cannot be empty/i),
    ).toBeInTheDocument();

    // Type into the input — error should disappear
    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "h" } });

    expect(
      screen.queryByText(/username cannot be empty/i),
    ).not.toBeInTheDocument();
  });

  it("calls fetchProfile for username input and updates context", async () => {
    mockApi.fetchProfile.mockResolvedValue(FETCH_RESULT);
    mockApi.getGames.mockResolvedValue(SAMPLE_GAMES);

    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "hikaru" } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    await waitFor(() => {
      expect(mockApi.fetchProfile).toHaveBeenCalledWith("hikaru");
    });
    expect(mockApi.getGames).toHaveBeenCalled();
  });

  it("calls fetchGameByUrl for URL input", async () => {
    const gameUrl = "https://www.chess.com/game/live/12345";
    mockApi.fetchGameByUrl.mockResolvedValue(FETCH_RESULT);
    mockApi.getGames.mockResolvedValue(SAMPLE_GAMES);

    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: gameUrl } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    await waitFor(() => {
      expect(mockApi.fetchGameByUrl).toHaveBeenCalledWith(gameUrl);
    });
    expect(mockApi.getGames).toHaveBeenCalled();
  });

  it("shows loading state during fetch", async () => {
    // Make the fetch hang until we resolve it
    let resolveFetch!: (value: FetchResult) => void;
    mockApi.fetchProfile.mockReturnValue(
      new Promise<FetchResult>((resolve) => {
        resolveFetch = resolve;
      }),
    );

    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "hikaru" } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    // Loading state should be visible
    expect(await screen.findByLabelText(/loading/i)).toBeInTheDocument();
    // Input and button should be disabled
    expect(input).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();

    // Resolve the fetch
    mockApi.getGames.mockResolvedValue([]);
    resolveFetch(FETCH_RESULT);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /load games/i })).toBeEnabled();
    });
  });

  it("shows inline error on API failure", async () => {
    mockApi.fetchProfile.mockRejectedValue(
      new ApiError(404, "username_not_found", "Username was not found on chess.com"),
    );

    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "nonexistent_user" } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    expect(
      await screen.findByText(/username was not found on chess\.com/i),
    ).toBeInTheDocument();
  });

  it("shows inline error for network errors", async () => {
    mockApi.fetchProfile.mockRejectedValue(new TypeError("Failed to fetch"));

    renderProfileInput();

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    fireEvent.change(input, { target: { value: "hikaru" } });
    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    expect(
      await screen.findByText(/failed to fetch/i),
    ).toBeInTheDocument();
  });

  it("error message has role=alert for accessibility", async () => {
    renderProfileInput();

    fireEvent.click(screen.getByRole("button", { name: /load games/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/username cannot be empty/i);
  });

  it("sets aria-invalid on input when error is shown", async () => {
    renderProfileInput();

    fireEvent.click(screen.getByRole("button", { name: /load games/i }));
    await screen.findByRole("alert");

    const input = screen.getByLabelText(/chess\.com username or game url/i);
    expect(input).toHaveAttribute("aria-invalid", "true");
  });
});
