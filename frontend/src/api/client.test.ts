/**
 * Unit tests for the Chess Review Engine API client.
 *
 * Tests cover:
 * - All REST API methods with correct URL, method, and body
 * - Error interceptor: structured API errors, network errors, timeouts
 * - Toast notifications on network and timeout errors
 * - SSE EventSource creation for progress streams
 * - Exponential backoff reconnection behaviour
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type {
  AnalysisStatus,
  FetchResult,
  GameAnalysis,
  GameSummary,
  PlayerAnalysisSummary,
} from "../types/index.ts";
import { ApiError, createApiClient } from "./client.ts";
import * as toastModule from "./toast.ts";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal valid GameSummary for testing. */
function makeGameSummary(overrides?: Partial<GameSummary>): GameSummary {
  return {
    game_id: "g1",
    date_played: "2024-01-15T12:00:00Z",
    opponent: "opponent1",
    result: "win",
    time_control: "600",
    opening_name: "Sicilian Defense",
    is_analyzed: false,
    ...overrides,
  };
}

function makePlayerSummary(): PlayerAnalysisSummary {
  return {
    best_count: 5,
    excellent_count: 3,
    good_count: 2,
    inaccuracy_count: 1,
    mistake_count: 0,
    blunder_count: 0,
    performance_ratings: [1500, 1520],
    final_performance_rating: 1520,
  };
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

let fetchSpy: ReturnType<typeof vi.fn>;
let toastSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  toastSpy = vi.spyOn(toastModule, "showToast").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// REST API Tests
// ---------------------------------------------------------------------------

describe("REST API methods", () => {
  const client = createApiClient("/api");

  // --- fetchProfile -------------------------------------------------------

  describe("fetchProfile", () => {
    it("sends POST to /api/games/fetch-profile with username", async () => {
      const expected: FetchResult = { games_count: 42, message: "ok" };
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(expected), { status: 200 }),
      );

      const result = await client.fetchProfile("testuser");

      expect(fetchSpy).toHaveBeenCalledWith("/api/games/fetch-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "testuser" }),
      });
      expect(result).toEqual(expected);
    });
  });

  // --- fetchGameByUrl -----------------------------------------------------

  describe("fetchGameByUrl", () => {
    it("sends POST to /api/games/fetch-url with url", async () => {
      const expected: FetchResult = { games_count: 1, message: "loaded" };
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(expected), { status: 200 }),
      );

      const result = await client.fetchGameByUrl(
        "https://www.chess.com/game/live/12345",
      );

      expect(fetchSpy).toHaveBeenCalledWith("/api/games/fetch-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: "https://www.chess.com/game/live/12345" }),
      });
      expect(result).toEqual(expected);
    });
  });

  // --- getGames -----------------------------------------------------------

  describe("getGames", () => {
    it("sends GET to /api/games without params by default", async () => {
      const expected: GameSummary[] = [makeGameSummary()];
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(expected), { status: 200 }),
      );

      const result = await client.getGames();

      expect(fetchSpy).toHaveBeenCalledWith("/api/games", undefined);
      expect(result).toEqual(expected);
    });

    it("appends sort_by and order query parameters", async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 }),
      );

      await client.getGames("date", "asc");

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/games?sort_by=date&order=asc",
        undefined,
      );
    });

    it("appends only sort_by when order is omitted", async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify([]), { status: 200 }),
      );

      await client.getGames("result");

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/games?sort_by=result",
        undefined,
      );
    });
  });

  // --- startAnalysis ------------------------------------------------------

  describe("startAnalysis", () => {
    it("sends POST to /api/analysis/{gameId}", async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(null), { status: 200 }),
      );

      await client.startAnalysis("game-123");

      expect(fetchSpy).toHaveBeenCalledWith("/api/analysis/game-123", {
        method: "POST",
      });
    });

    it("encodes special characters in gameId", async () => {
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(null), { status: 200 }),
      );

      await client.startAnalysis("game/id with spaces");

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/analysis/game%2Fid%20with%20spaces",
        { method: "POST" },
      );
    });
  });

  // --- getAnalysisStatus --------------------------------------------------

  describe("getAnalysisStatus", () => {
    it("sends GET to /api/analysis/{gameId}/status", async () => {
      const expected: AnalysisStatus = {
        game_id: "g1",
        total_positions: 80,
        positions_analyzed: 40,
        is_complete: false,
        percentage: 50,
      };
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(expected), { status: 200 }),
      );

      const result = await client.getAnalysisStatus("g1");

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/analysis/g1/status",
        undefined,
      );
      expect(result).toEqual(expected);
    });
  });

  // --- getAnalysis --------------------------------------------------------

  describe("getAnalysis", () => {
    it("sends GET to /api/analysis/{gameId}", async () => {
      const expected: GameAnalysis = {
        game_id: "g1",
        moves: [],
        white_summary: makePlayerSummary(),
        black_summary: makePlayerSummary(),
        evaluations: [],
        is_complete: true,
      };
      fetchSpy.mockResolvedValueOnce(
        new Response(JSON.stringify(expected), { status: 200 }),
      );

      const result = await client.getAnalysis("g1");

      expect(fetchSpy).toHaveBeenCalledWith("/api/analysis/g1", undefined);
      expect(result).toEqual(expected);
    });
  });
});

// ---------------------------------------------------------------------------
// Error Handling Tests
// ---------------------------------------------------------------------------

describe("Error handling", () => {
  const client = createApiClient("/api");

  it("throws ApiError with parsed body on structured API errors", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: "invalid_username",
          message: "Username must be 1-25 characters",
        }),
        { status: 400 },
      ),
    );

    await expect(client.fetchProfile("")).rejects.toThrow(ApiError);

    try {
      await client.fetchProfile("");
    } catch (e) {
      // fetchSpy needs a fresh response for the second call
    }
  });

  it("extracts error code and message from structured 400 response", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: "invalid_username",
          message: "Username must be 1-25 characters",
        }),
        { status: 400 },
      ),
    );

    try {
      await client.fetchProfile("");
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.status).toBe(400);
      expect(apiErr.errorCode).toBe("invalid_username");
      expect(apiErr.message).toBe("Username must be 1-25 characters");
    }
  });

  it("handles non-JSON error body gracefully", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response("Internal Server Error", { status: 500 }),
    );

    try {
      await client.getGames();
      expect.unreachable("Should have thrown");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const apiErr = e as ApiError;
      expect(apiErr.status).toBe(500);
      expect(apiErr.errorCode).toBe("unknown_error");
    }
  });

  it("shows toast on 504 upstream timeout", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: "upstream_timeout",
          message: "Connection to chess.com failed",
        }),
        { status: 504 },
      ),
    );

    await expect(client.fetchProfile("user")).rejects.toThrow(ApiError);
    expect(toastSpy).toHaveBeenCalledWith("Connection to chess.com failed");
  });

  it("shows toast on 502 upstream unreachable", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: "upstream_unreachable",
          message: "Connection to chess.com failed",
        }),
        { status: 502 },
      ),
    );

    await expect(client.fetchProfile("user")).rejects.toThrow(ApiError);
    expect(toastSpy).toHaveBeenCalledWith("Connection to chess.com failed");
  });

  it("shows toast on network error (fetch throws TypeError)", async () => {
    fetchSpy.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(client.getGames()).rejects.toThrow(TypeError);
    expect(toastSpy).toHaveBeenCalledWith("Failed to fetch");
  });

  it("does not show toast on 404 errors", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          error: "username_not_found",
          message: "Username was not found on chess.com",
        }),
        { status: 404 },
      ),
    );

    await expect(client.fetchProfile("noone")).rejects.toThrow(ApiError);
    expect(toastSpy).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// SSE Tests
// ---------------------------------------------------------------------------

describe("SSE stream methods", () => {
  // Mock EventSource at the global level
  interface MockEventSourceInstance {
    url: string;
    onmessage: ((ev: MessageEvent) => void) | null;
    onerror: ((ev: Event) => void) | null;
    onopen: ((ev: Event) => void) | null;
    readyState: number;
    close: ReturnType<typeof vi.fn>;
    addEventListener: ReturnType<typeof vi.fn>;
    removeEventListener: ReturnType<typeof vi.fn>;
  }

  let mockEventSourceInstances: MockEventSourceInstance[];

  beforeEach(() => {
    mockEventSourceInstances = [];

    // Must use `function` (not arrow) so it can be called with `new`
    function MockEventSource(this: MockEventSourceInstance, url: string) {
      this.url = url;
      this.onmessage = null;
      this.onerror = null;
      this.onopen = null;
      this.readyState = 0; // CONNECTING
      this.close = vi.fn();
      this.addEventListener = vi.fn();
      this.removeEventListener = vi.fn();
      mockEventSourceInstances.push(this);
    }

    // Static constants required by the production code
    MockEventSource.CONNECTING = 0;
    MockEventSource.OPEN = 1;
    MockEventSource.CLOSED = 2;

    vi.stubGlobal("EventSource", MockEventSource);
  });

  const client = createApiClient("/api");

  it("streamFetchProgress creates EventSource with correct URL", () => {
    const source = client.streamFetchProgress("testuser");

    expect(mockEventSourceInstances).toHaveLength(1);
    expect(mockEventSourceInstances[0].url).toBe(
      "/api/stream/fetch/testuser",
    );

    source.close();
  });

  it("streamFetchProgress encodes username", () => {
    const source = client.streamFetchProgress("user name");

    expect(mockEventSourceInstances[0].url).toBe(
      "/api/stream/fetch/user%20name",
    );

    source.close();
  });

  it("streamAnalysisProgress creates EventSource with correct URL", () => {
    const source = client.streamAnalysisProgress("game-42");

    expect(mockEventSourceInstances).toHaveLength(1);
    expect(mockEventSourceInstances[0].url).toBe(
      "/api/stream/analysis/game-42",
    );

    source.close();
  });

  it("close() on returned source closes the underlying EventSource", () => {
    const source = client.streamFetchProgress("testuser");
    source.close();

    expect(mockEventSourceInstances[0].close).toHaveBeenCalled();
  });

  it("delegates onmessage to the underlying EventSource", () => {
    const source = client.streamFetchProgress("testuser");
    const handler = vi.fn();
    source.onmessage = handler;

    expect(mockEventSourceInstances[0].onmessage).toBe(handler);

    source.close();
  });

  it("shows toast and reconnects when SSE connection drops", () => {
    vi.useFakeTimers();

    const source = client.streamFetchProgress("testuser");

    // Simulate connection closing
    mockEventSourceInstances[0].readyState = 2; // CLOSED
    const errorHandler = mockEventSourceInstances[0].onerror;
    if (errorHandler) {
      errorHandler(new Event("error"));
    }

    expect(toastSpy).toHaveBeenCalledWith(
      "Connection to server lost. Reconnecting…",
    );

    // After 1s delay a new EventSource should be created
    vi.advanceTimersByTime(1000);
    expect(mockEventSourceInstances).toHaveLength(2);
    expect(mockEventSourceInstances[1].url).toBe(
      "/api/stream/fetch/testuser",
    );

    source.close();
    vi.useRealTimers();
  });

  it("applies exponential backoff on repeated failures", () => {
    vi.useFakeTimers();

    const source = client.streamFetchProgress("testuser");

    // First failure → 1s delay
    mockEventSourceInstances[0].readyState = 2;
    mockEventSourceInstances[0].onerror?.(new Event("error"));
    vi.advanceTimersByTime(1000);
    expect(mockEventSourceInstances).toHaveLength(2);

    // Second failure → 2s delay
    mockEventSourceInstances[1].readyState = 2;
    mockEventSourceInstances[1].onerror?.(new Event("error"));
    vi.advanceTimersByTime(1999);
    expect(mockEventSourceInstances).toHaveLength(2); // not yet
    vi.advanceTimersByTime(1);
    expect(mockEventSourceInstances).toHaveLength(3);

    // Third failure → 4s delay
    mockEventSourceInstances[2].readyState = 2;
    mockEventSourceInstances[2].onerror?.(new Event("error"));
    vi.advanceTimersByTime(3999);
    expect(mockEventSourceInstances).toHaveLength(3);
    vi.advanceTimersByTime(1);
    expect(mockEventSourceInstances).toHaveLength(4);

    source.close();
    vi.useRealTimers();
  });

  it("does not reconnect after close() is called", () => {
    vi.useFakeTimers();

    const source = client.streamFetchProgress("testuser");
    source.close();

    // Simulate error after close
    mockEventSourceInstances[0].readyState = 2;
    mockEventSourceInstances[0].onerror?.(new Event("error"));

    vi.advanceTimersByTime(30_000);
    expect(mockEventSourceInstances).toHaveLength(1); // No reconnection

    vi.useRealTimers();
  });
});
