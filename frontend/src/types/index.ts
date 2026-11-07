/**
 * Frontend TypeScript types for the Chess Review Engine.
 *
 * These interfaces mirror the backend Python domain models defined in the
 * design document to ensure consistent data exchange over the REST API.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/**
 * Classification of a move based on centipawn loss thresholds.
 *
 * Thresholds (centipawn loss):
 *   best       = 0
 *   excellent  = 1–10
 *   good       = 11–30
 *   inaccuracy = 31–80
 *   mistake    = 81–200
 *   blunder    = 201+
 */
export const MoveClassification = {
  Best: "best",
  Excellent: "excellent",
  Good: "good",
  Inaccuracy: "inaccuracy",
  Mistake: "mistake",
  Blunder: "blunder",
} as const;

export type MoveClassification =
  (typeof MoveClassification)[keyof typeof MoveClassification];

/** Game outcome from the fetched player's perspective. */
export const GameResult = {
  Win: "win",
  Loss: "loss",
  Draw: "draw",
} as const;

export type GameResult = (typeof GameResult)[keyof typeof GameResult];

// ---------------------------------------------------------------------------
// Sort types
// ---------------------------------------------------------------------------

/** Fields available for sorting the game list. */
export type SortField = "date" | "result" | "time_control";

/** Sort direction. */
export type SortOrder = "asc" | "desc";

// ---------------------------------------------------------------------------
// Domain interfaces
// ---------------------------------------------------------------------------

/** Summary info for a single game in the game list. */
export interface GameSummary {
  game_id: string;
  date_played: string; // ISO 8601 date-time from the API
  opponent: string;
  result: GameResult;
  time_control: string | null;
  opening_name: string | null;
  is_analyzed: boolean;
}

/** A candidate move suggested by Stockfish. */
export interface CandidateMove {
  move_san: string;
  evaluation: number | null; // centipawns
  mate_in: number | null;
}

/** Stockfish evaluation of a single position. */
export interface PositionEvaluation {
  fen: string;
  evaluation: number | null; // centipawns from White's perspective
  mate_in: number | null; // positive = White mates, negative = Black mates
  candidate_moves: CandidateMove[];
  is_error: boolean;
}

/** A single analyzed half-move in the game. */
export interface AnalyzedMove {
  move_number: number;
  is_white: boolean;
  move_san: string;
  position_before: string; // FEN
  position_after: string; // FEN
  evaluation_before: PositionEvaluation;
  evaluation_after: PositionEvaluation;
  classification: MoveClassification | null;
  centipawn_loss: number | null;
  candidate_moves: CandidateMove[];
  insight: LearningInsight | null;
}

/** Explanation for a suboptimal move. */
export interface LearningInsight {
  move_number: number;
  is_white: boolean;
  played_move: string;
  best_move: string;
  centipawn_loss: number;
  classification: MoveClassification;
  principal_variation: string[]; // up to 5 moves
  explanation: string;
}

/** Per-player summary of analysis results. */
export interface PlayerAnalysisSummary {
  best_count: number;
  excellent_count: number;
  good_count: number;
  inaccuracy_count: number;
  mistake_count: number;
  blunder_count: number;
  performance_ratings: number[]; // cumulative after each of the player's moves
  final_performance_rating: number;
}

/** Complete analysis results for a game. */
export interface GameAnalysis {
  game_id: string;
  moves: AnalyzedMove[];
  white_summary: PlayerAnalysisSummary;
  black_summary: PlayerAnalysisSummary;
  evaluations: (number | null)[]; // centipawn per half-move for graph
  is_complete: boolean;
}

/** Progress of an ongoing analysis. */
export interface AnalysisStatus {
  game_id: string;
  total_positions: number;
  positions_analyzed: number;
  is_complete: boolean;
  percentage: number; // 0–100
}

/** Result returned by game-fetch operations. */
export interface FetchResult {
  games_count: number;
  message: string;
}

// ---------------------------------------------------------------------------
// API client interface
// ---------------------------------------------------------------------------

/** Contract for all frontend ↔ backend communication. */
export interface ChessReviewAPI {
  // Game Fetching
  fetchProfile(username: string): Promise<FetchResult>;
  fetchGameByUrl(url: string): Promise<FetchResult>;
  getGames(sortBy?: SortField, order?: SortOrder): Promise<GameSummary[]>;

  // Analysis
  startAnalysis(gameId: string): Promise<void>;
  getAnalysisStatus(gameId: string): Promise<AnalysisStatus>;
  getAnalysis(gameId: string): Promise<GameAnalysis>;

  // Server-Sent Events for progress
  streamFetchProgress(username: string): EventSource;
  streamAnalysisProgress(gameId: string): EventSource;
}
