/**
 * Frontend API client with SSE support for the Chess Review Engine.
 *
 * Implements the {@link ChessReviewAPI} interface defined in types/index.ts.
 * Uses the Fetch API for REST calls and EventSource for SSE streams with
 * exponential backoff reconnection (1s → 2s → 4s → … → max 30s).
 *
 * Requirements: 1.9, 5.5
 */

import type {
  AnalysisStatus,
  ChessReviewAPI,
  FetchResult,
  GameAnalysis,
  GameSummary,
  SortField,
  SortOrder,
} from "../types/index.ts";
import { showToast } from "./toast.ts";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const BASE_URL = "/api";

/** Initial reconnection delay for SSE in milliseconds. */
const SSE_INITIAL_DELAY_MS = 1000;

/** Maximum reconnection delay for SSE in milliseconds. */
const SSE_MAX_DELAY_MS = 30_000;

// ---------------------------------------------------------------------------
// Shared error handling
// ---------------------------------------------------------------------------

/** Structured error returned by the backend API. */
interface ApiErrorBody {
  error: string;
  message: string;
}

/** Error thrown when an API call fails. */
export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

/**
 * Shared error interceptor for all REST calls.
 *
 * On network / timeout errors a toast is shown and the error is re-thrown.
 * On non-OK HTTP responses the body is parsed for a structured error and
 * an {@link ApiError} is thrown with the details.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorCode = "unknown_error";
    let errorMessage = `Request failed with status ${response.status}`;

    try {
      const body = (await response.json()) as ApiErrorBody;
      errorCode = body.error ?? errorCode;
      errorMessage = body.message ?? errorMessage;
    } catch {
      // Body was not JSON — keep defaults.
    }

    throw new ApiError(response.status, errorCode, errorMessage);
  }

  return response.json() as Promise<T>;
}

/**
 * Wrapper around `fetch` that surfaces network & timeout errors as toasts.
 */
async function apiFetch<T>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  try {
    const response = await fetch(url, init);
    return await handleResponse<T>(response);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      // Surface server-side errors as toasts too for network-level codes
      if (error.status === 504 || error.status === 502) {
        showToast(error.message);
      }
      throw error;
    }

    // Network error or timeout (TypeError from fetch)
    const message =
      error instanceof Error
        ? error.message
        : "An unexpected network error occurred";
    showToast(message);
    throw error;
  }
}

// ---------------------------------------------------------------------------
// SSE with exponential backoff
// ---------------------------------------------------------------------------

/**
 * Creates a reconnecting EventSource wrapper.
 *
 * The native EventSource auto-reconnects, but we implement manual reconnection
 * with exponential backoff (1s, 2s, 4s, … max 30s) so we have precise control
 * over the timing and can show toast notifications on errors.
 *
 * Returns a plain EventSource for the caller. If the connection drops, a new
 * EventSource is created transparently and the caller's `onmessage` / `onerror`
 * handlers are rebound.
 */
function createReconnectingEventSource(url: string): EventSource {
  let delay = SSE_INITIAL_DELAY_MS;
  let currentSource = new EventSource(url);
  let closed = false;

  // Preserve caller-set handlers across reconnections
  let userOnMessage: ((ev: MessageEvent) => void) | null = null;
  let userOnError: ((ev: Event) => void) | null = null;
  let userOnOpen: ((ev: Event) => void) | null = null;

  function reconnect(): void {
    if (closed) return;

    setTimeout(() => {
      if (closed) return;

      const newSource = new EventSource(url);

      // Re-bind preserved handlers
      if (userOnMessage) newSource.onmessage = userOnMessage;
      if (userOnOpen) newSource.onopen = userOnOpen;

      newSource.onerror = handleError;

      // On successful reconnection reset the delay
      newSource.onopen = (ev: Event) => {
        delay = SSE_INITIAL_DELAY_MS;
        if (userOnOpen) userOnOpen(ev);
      };

      currentSource = newSource;
    }, delay);

    // Exponential backoff: 1s → 2s → 4s → … → 30s max
    delay = Math.min(delay * 2, SSE_MAX_DELAY_MS);
  }

  function handleError(_ev: Event): void {
    if (closed) return;

    // EventSource.CLOSED === 2
    if (currentSource.readyState === EventSource.CLOSED) {
      showToast("Connection to server lost. Reconnecting…");
      reconnect();
    }

    // Delegate to user handler if set
    if (userOnError) userOnError(_ev);
  }

  currentSource.onerror = handleError;

  // Return a Proxy so the caller can set onmessage/onerror/onopen and
  // call close() on a stable reference even after internal reconnections.
  const proxy = new Proxy(currentSource, {
    get(target, prop, receiver) {
      // Always read from the *current* source for state properties
      if (prop === "readyState" || prop === "url" || prop === "withCredentials") {
        return Reflect.get(currentSource, prop);
      }

      if (prop === "close") {
        return () => {
          closed = true;
          currentSource.close();
        };
      }

      if (prop === "onmessage") return userOnMessage;
      if (prop === "onerror") return userOnError;
      if (prop === "onopen") return userOnOpen;

      if (prop === "addEventListener") {
        return (type: string, listener: EventListenerOrEventListenerObject, options?: boolean | AddEventListenerOptions) => {
          currentSource.addEventListener(type, listener, options);
        };
      }

      if (prop === "removeEventListener") {
        return (type: string, listener: EventListenerOrEventListenerObject, options?: boolean | EventListenerOptions) => {
          currentSource.removeEventListener(type, listener, options);
        };
      }

      return Reflect.get(target, prop, receiver);
    },

    set(_target, prop, value) {
      if (prop === "onmessage") {
        userOnMessage = value as ((ev: MessageEvent) => void) | null;
        currentSource.onmessage = value as ((ev: MessageEvent) => void) | null;
        return true;
      }
      if (prop === "onerror") {
        userOnError = value as ((ev: Event) => void) | null;
        // Don't overwrite internal handler — it calls userOnError itself
        return true;
      }
      if (prop === "onopen") {
        userOnOpen = value as ((ev: Event) => void) | null;
        return true;
      }
      return true;
    },
  });

  return proxy as unknown as EventSource;
}

// ---------------------------------------------------------------------------
// API Client implementation
// ---------------------------------------------------------------------------

/**
 * Create an API client implementing the {@link ChessReviewAPI} interface.
 *
 * @param baseUrl - Optional base URL override (defaults to "/api").
 */
export function createApiClient(baseUrl: string = BASE_URL): ChessReviewAPI {
  const json = { "Content-Type": "application/json" };

  return {
    // -----------------------------------------------------------------------
    // Game Fetching
    // -----------------------------------------------------------------------

    async fetchProfile(username: string): Promise<FetchResult> {
      return apiFetch<FetchResult>(`${baseUrl}/games/fetch-profile`, {
        method: "POST",
        headers: json,
        body: JSON.stringify({ username }),
      });
    },

    async fetchGameByUrl(url: string): Promise<FetchResult> {
      return apiFetch<FetchResult>(`${baseUrl}/games/fetch-url`, {
        method: "POST",
        headers: json,
        body: JSON.stringify({ url }),
      });
    },

    async getGames(
      sortBy?: SortField,
      order?: SortOrder,
    ): Promise<GameSummary[]> {
      const params = new URLSearchParams();
      if (sortBy) params.set("sort_by", sortBy);
      if (order) params.set("order", order);
      const qs = params.toString();
      const url = qs ? `${baseUrl}/games?${qs}` : `${baseUrl}/games`;
      return apiFetch<GameSummary[]>(url);
    },

    // -----------------------------------------------------------------------
    // Analysis
    // -----------------------------------------------------------------------

    async startAnalysis(gameId: string): Promise<void> {
      await apiFetch<void>(`${baseUrl}/analysis/${encodeURIComponent(gameId)}`, {
        method: "POST",
      });
    },

    async getAnalysisStatus(gameId: string): Promise<AnalysisStatus> {
      return apiFetch<AnalysisStatus>(
        `${baseUrl}/analysis/${encodeURIComponent(gameId)}/status`,
      );
    },

    async getAnalysis(gameId: string): Promise<GameAnalysis> {
      return apiFetch<GameAnalysis>(
        `${baseUrl}/analysis/${encodeURIComponent(gameId)}`,
      );
    },

    // -----------------------------------------------------------------------
    // SSE Streams
    // -----------------------------------------------------------------------

    streamFetchProgress(username: string): EventSource {
      return createReconnectingEventSource(
        `${baseUrl}/stream/fetch/${encodeURIComponent(username)}`,
      );
    },

    streamAnalysisProgress(gameId: string): EventSource {
      return createReconnectingEventSource(
        `${baseUrl}/stream/analysis/${encodeURIComponent(gameId)}`,
      );
    },
  };
}

/** Default singleton API client instance. */
export const api: ChessReviewAPI = createApiClient();
