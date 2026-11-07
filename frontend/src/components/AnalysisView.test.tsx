import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AnalysisView from "./AnalysisView";
import type {
  GameAnalysis,
  AnalysisStatus,
  PlayerAnalysisSummary,
  AnalyzedMove,
  PositionEvaluation,
} from "../types";

// ---------------------------------------------------------------------------
// Mock the API client
// ---------------------------------------------------------------------------

const mockStartAnalysis = vi.fn();
const mockGetAnalysisStatus = vi.fn();
const mockGetAnalysis = vi.fn();
const mockStreamAnalysisProgress = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    startAnalysis: (...args: unknown[]) => mockStartAnalysis(...args),
    getAnalysisStatus: (...args: unknown[]) => mockGetAnalysisStatus(...args),
    getAnalysis: (...args: unknown[]) => mockGetAnalysis(...args),
    streamAnalysisProgress: (...args: unknown[]) => mockStreamAnalysisProgress(...args),
  },
}));

// ---------------------------------------------------------------------------
// Mock child components to keep tests focused on AnalysisView logic
// ---------------------------------------------------------------------------

vi.mock("./ChessBoard", () => ({
  default: (props: { fen: string }) => (
    <div data-testid="mock-chessboard" data-fen={props.fen} />
  ),
}));

vi.mock("./MoveNavigator", () => ({
  default: (props: { currentMove: number; totalMoves: number; onNavigate: (i: number) => void }) => (
    <div data-testid="mock-move-navigator" data-current={props.currentMove} data-total={props.totalMoves}>
      <button data-testid="nav-next" onClick={() => props.onNavigate(props.currentMove + 1)}>Next</button>
      <button data-testid="nav-prev" onClick={() => props.onNavigate(props.currentMove - 1)}>Prev</button>
      <button data-testid="nav-to-2" onClick={() => props.onNavigate(2)}>Go to 2</button>
    </div>
  ),
}));

vi.mock("./MoveList", () => ({
  default: (props: { currentMove: number; onSelect: (i: number) => void }) => (
    <div data-testid="mock-move-list" data-current={props.currentMove}>
      <button data-testid="select-move-1" onClick={() => props.onSelect(1)}>Select 1</button>
    </div>
  ),
}));

vi.mock("./CandidateMoves", () => ({
  default: (props: { playerMove: string }) => (
    <div data-testid="mock-candidate-moves" data-player-move={props.playerMove} />
  ),
}));

vi.mock("./InsightPanel", () => ({
  default: (props: { insight: unknown }) => (
    <div data-testid="mock-insight-panel" data-has-insight={props.insight !== null ? "true" : "false"} />
  ),
}));

vi.mock("./GameSummary", () => ({
  default: () => <div data-testid="mock-game-summary" />,
}));

vi.mock("./EvaluationGraph", () => ({
  default: (props: { currentMove: number; onClick: (i: number) => void }) => (
    <div data-testid="mock-eval-graph" data-current={props.currentMove}>
      <button data-testid="graph-click-3" onClick={() => props.onClick(3)}>Click 3</button>
    </div>
  ),
}));

vi.mock("./PerformanceGraph", () => ({
  default: (props: { currentMove: number }) => (
    <div data-testid="mock-perf-graph" data-current={props.currentMove} />
  ),
}));

vi.mock("./ProgressIndicator", () => ({
  default: (props: { progress: number; type: string }) => (
    <div data-testid="mock-progress-indicator" data-progress={props.progress} data-type={props.type} />
  ),
}));

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function makePositionEval(overrides: Partial<PositionEvaluation> = {}): PositionEvaluation {
  return {
    fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    evaluation: 20,
    mate_in: null,
    candidate_moves: [
      { move_san: "e4", evaluation: 30, mate_in: null },
      { move_san: "d4", evaluation: 20, mate_in: null },
    ],
    is_error: false,
    ...overrides,
  };
}

function makeAnalyzedMove(index: number, overrides: Partial<AnalyzedMove> = {}): AnalyzedMove {
  return {
    move_number: Math.floor(index / 2) + 1,
    is_white: index % 2 === 0,
    move_san: index % 2 === 0 ? "e4" : "e5",
    position_before: "start-fen",
    position_after: `fen-after-move-${index}`,
    evaluation_before: makePositionEval(),
    evaluation_after: makePositionEval({ evaluation: 10 + index * 5 }),
    classification: "good",
    centipawn_loss: 15,
    candidate_moves: [
      { move_san: "e4", evaluation: 30, mate_in: null },
      { move_san: "d4", evaluation: 20, mate_in: null },
    ],
    insight: null,
    ...overrides,
  };
}

function makeSummary(overrides: Partial<PlayerAnalysisSummary> = {}): PlayerAnalysisSummary {
  return {
    best_count: 5,
    excellent_count: 3,
    good_count: 4,
    inaccuracy_count: 2,
    mistake_count: 1,
    blunder_count: 0,
    performance_ratings: [1500, 1520],
    final_performance_rating: 1510,
    ...overrides,
  };
}

function makeGameAnalysis(moveCount: number = 4): GameAnalysis {
  const moves = Array.from({ length: moveCount }, (_, i) => makeAnalyzedMove(i));
  return {
    game_id: "game-123",
    moves,
    white_summary: makeSummary(),
    black_summary: makeSummary(),
    evaluations: moves.map((_, i) => 10 + i * 5),
    is_complete: true,
  };
}

function makeStatus(overrides: Partial<AnalysisStatus> = {}): AnalysisStatus {
  return {
    game_id: "game-123",
    total_positions: 80,
    positions_analyzed: 0,
    is_complete: false,
    percentage: 0,
    ...overrides,
  };
}

/** Create a mock EventSource that allows manual message dispatch. */
function createMockEventSource() {
  let onmessage: ((ev: MessageEvent) => void) | null = null;
  let onerror: ((ev: Event) => void) | null = null;
  const source = {
    get onmessage() { return onmessage; },
    set onmessage(fn: ((ev: MessageEvent) => void) | null) { onmessage = fn; },
    get onerror() { return onerror; },
    set onerror(fn: ((ev: Event) => void) | null) { onerror = fn; },
    close: vi.fn(),
    readyState: 1, // EventSource.OPEN = 1
    /** Simulate receiving an SSE message. */
    _emit(data: unknown) {
      if (onmessage) {
        onmessage(new MessageEvent("message", { data: JSON.stringify(data) }));
      }
    },
  };
  return source;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("AnalysisView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset module-level ref between tests
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -----------------------------------------------------------------------
  // Loading → Complete (analysis already done)
  // -----------------------------------------------------------------------

  it("shows loading state initially then complete when analysis is already done", async () => {
    const analysis = makeGameAnalysis();

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    // Initially loading
    expect(screen.getByTestId("analysis-loading")).toBeInTheDocument();

    // After async init, should show complete view
    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // No progress indicator in complete phase (Req 5.6)
    expect(screen.queryByTestId("mock-progress-indicator")).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Loading → Analyzing (SSE progress)
  // -----------------------------------------------------------------------

  it("shows progress indicator during analysis phase", async () => {
    const mockSSE = createMockEventSource();

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ percentage: 25 }));
    mockStreamAnalysisProgress.mockReturnValueOnce(mockSSE);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("mock-progress-indicator")).toBeInTheDocument();
    });

    const indicator = screen.getByTestId("mock-progress-indicator");
    expect(indicator).toHaveAttribute("data-type", "analysis");

    // No analysis-complete view during analyzing (Req 5.6)
    expect(screen.queryByTestId("analysis-complete")).not.toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // SSE → Complete transition (atomic replacement — Req 5.6)
  // -----------------------------------------------------------------------

  it("atomically replaces progress with results when SSE signals completion", async () => {
    const mockSSE = createMockEventSource();
    const analysis = makeGameAnalysis();

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ percentage: 50 }));
    mockStreamAnalysisProgress.mockReturnValueOnce(mockSSE);
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    // Wait for analyzing phase
    await waitFor(() => {
      expect(screen.getByTestId("mock-progress-indicator")).toBeInTheDocument();
    });

    // SSE sends completion event
    await act(async () => {
      mockSSE._emit({ percentage: 100, is_complete: true });
    });

    // Should transition to complete
    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Progress indicator is gone (atomic replacement — Req 5.6)
    expect(screen.queryByTestId("mock-progress-indicator")).not.toBeInTheDocument();

    // SSE should be closed
    expect(mockSSE.close).toHaveBeenCalled();
  });

  // -----------------------------------------------------------------------
  // 409 Conflict: analysis already in progress → still subscribes to SSE
  // -----------------------------------------------------------------------

  it("handles 409 conflict (analysis already running) and subscribes to SSE", async () => {
    const conflictError = { status: 409, message: "Already in progress" };
    const mockSSE = createMockEventSource();

    mockStartAnalysis.mockRejectedValueOnce(conflictError);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ percentage: 40 }));
    mockStreamAnalysisProgress.mockReturnValueOnce(mockSSE);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("mock-progress-indicator")).toBeInTheDocument();
    });

    // Should still be in analyzing phase
    expect(screen.getByTestId("mock-progress-indicator")).toHaveAttribute("data-progress", "40");
  });

  // -----------------------------------------------------------------------
  // Error handling
  // -----------------------------------------------------------------------

  it("shows error message when startAnalysis fails with non-409 error", async () => {
    mockStartAnalysis.mockRejectedValueOnce(new Error("Network error"));

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-error")).toBeInTheDocument();
    });

    expect(screen.getByTestId("analysis-error")).toHaveTextContent("Network error");
  });

  // -----------------------------------------------------------------------
  // Move index synchronization across components
  // -----------------------------------------------------------------------

  it("synchronizes currentMoveIndex across all child components", async () => {
    const analysis = makeGameAnalysis(6);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Initially all at move 0
    expect(screen.getByTestId("mock-move-navigator")).toHaveAttribute("data-current", "0");
    expect(screen.getByTestId("mock-move-list")).toHaveAttribute("data-current", "0");
    expect(screen.getByTestId("mock-eval-graph")).toHaveAttribute("data-current", "0");
    expect(screen.getByTestId("mock-perf-graph")).toHaveAttribute("data-current", "0");
  });

  it("updates all components when navigating via MoveNavigator", async () => {
    const analysis = makeGameAnalysis(6);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Click Next button in the mocked MoveNavigator
    await act(async () => {
      screen.getByTestId("nav-next").click();
    });

    // All components should reflect move 1
    expect(screen.getByTestId("mock-move-navigator")).toHaveAttribute("data-current", "1");
    expect(screen.getByTestId("mock-move-list")).toHaveAttribute("data-current", "1");
    expect(screen.getByTestId("mock-eval-graph")).toHaveAttribute("data-current", "1");
    expect(screen.getByTestId("mock-perf-graph")).toHaveAttribute("data-current", "1");
  });

  it("updates all components when selecting from MoveList", async () => {
    const analysis = makeGameAnalysis(6);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Click select-move-1 button in mocked MoveList
    await act(async () => {
      screen.getByTestId("select-move-1").click();
    });

    // All should be at move 1
    expect(screen.getByTestId("mock-move-navigator")).toHaveAttribute("data-current", "1");
    expect(screen.getByTestId("mock-move-list")).toHaveAttribute("data-current", "1");
  });

  it("updates all components when clicking on EvaluationGraph", async () => {
    const analysis = makeGameAnalysis(6);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Click on graph at move index 3
    await act(async () => {
      screen.getByTestId("graph-click-3").click();
    });

    expect(screen.getByTestId("mock-move-navigator")).toHaveAttribute("data-current", "3");
    expect(screen.getByTestId("mock-eval-graph")).toHaveAttribute("data-current", "3");
  });

  // -----------------------------------------------------------------------
  // Correct data extraction for child components
  // -----------------------------------------------------------------------

  it("passes correct FEN for the current move to ChessBoard", async () => {
    const analysis = makeGameAnalysis(4);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Move 0 → position_after of moves[0]
    expect(screen.getByTestId("mock-chessboard")).toHaveAttribute("data-fen", "fen-after-move-0");
  });

  it("passes correct playerMove for CandidateMoves", async () => {
    const analysis = makeGameAnalysis(4);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Move 0 is white, so move_san = "e4"
    expect(screen.getByTestId("mock-candidate-moves")).toHaveAttribute("data-player-move", "e4");
  });

  it("passes insight for suboptimal moves to InsightPanel", async () => {
    const insight = {
      move_number: 3,
      is_white: false,
      played_move: "Qh4",
      best_move: "Nf6",
      centipawn_loss: 120,
      classification: "mistake" as const,
      principal_variation: ["Nf6", "Nc3", "Bb4"],
      explanation: "This loses a tempo",
    };

    const moves = [
      makeAnalyzedMove(0, { insight }),
      makeAnalyzedMove(1),
    ];

    const analysis: GameAnalysis = {
      game_id: "game-123",
      moves,
      white_summary: makeSummary(),
      black_summary: makeSummary(),
      evaluations: [20, 10],
      is_complete: true,
    };

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // Move 0 has an insight
    expect(screen.getByTestId("mock-insight-panel")).toHaveAttribute("data-has-insight", "true");
  });

  it("clears insight panel for moves without insights", async () => {
    const analysis = makeGameAnalysis(4); // all moves have insight: null

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    expect(screen.getByTestId("mock-insight-panel")).toHaveAttribute("data-has-insight", "false");
  });

  // -----------------------------------------------------------------------
  // SSE progress updates
  // -----------------------------------------------------------------------

  it("updates progress as SSE messages arrive", async () => {
    const mockSSE = createMockEventSource();

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ percentage: 10 }));
    mockStreamAnalysisProgress.mockReturnValueOnce(mockSSE);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("mock-progress-indicator")).toBeInTheDocument();
    });

    // Initial progress from status
    expect(screen.getByTestId("mock-progress-indicator")).toHaveAttribute("data-progress", "10");

    // SSE sends 50% update
    await act(async () => {
      mockSSE._emit({ percentage: 50, is_complete: false });
    });

    expect(screen.getByTestId("mock-progress-indicator")).toHaveAttribute("data-progress", "50");

    // SSE sends 75% update
    await act(async () => {
      mockSSE._emit({ percentage: 75, is_complete: false });
    });

    expect(screen.getByTestId("mock-progress-indicator")).toHaveAttribute("data-progress", "75");
  });

  // -----------------------------------------------------------------------
  // Renders all child components in complete phase
  // -----------------------------------------------------------------------

  it("renders all required child components in complete phase", async () => {
    const analysis = makeGameAnalysis(4);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    // All child components should be present
    expect(screen.getByTestId("mock-chessboard")).toBeInTheDocument();
    expect(screen.getByTestId("mock-move-navigator")).toBeInTheDocument();
    expect(screen.getByTestId("mock-move-list")).toBeInTheDocument();
    expect(screen.getByTestId("mock-candidate-moves")).toBeInTheDocument();
    expect(screen.getByTestId("mock-insight-panel")).toBeInTheDocument();
    expect(screen.getByTestId("mock-game-summary")).toBeInTheDocument();
    expect(screen.getByTestId("mock-eval-graph")).toBeInTheDocument();
    expect(screen.getByTestId("mock-perf-graph")).toBeInTheDocument();
  });

  // -----------------------------------------------------------------------
  // Passes correct totalMoves to MoveNavigator
  // -----------------------------------------------------------------------

  it("passes correct totalMoves to MoveNavigator", async () => {
    const analysis = makeGameAnalysis(10);

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(analysis);

    render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    expect(screen.getByTestId("mock-move-navigator")).toHaveAttribute("data-total", "10");
  });

  // -----------------------------------------------------------------------
  // SSE cleanup on unmount
  // -----------------------------------------------------------------------

  it("closes SSE connection on unmount", async () => {
    const mockSSE = createMockEventSource();

    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ percentage: 30 }));
    mockStreamAnalysisProgress.mockReturnValueOnce(mockSSE);

    const { unmount } = render(<AnalysisView gameId="game-123" />);

    await waitFor(() => {
      expect(screen.getByTestId("mock-progress-indicator")).toBeInTheDocument();
    });

    unmount();

    expect(mockSSE.close).toHaveBeenCalled();
  });

  // -----------------------------------------------------------------------
  // API calls with correct gameId
  // -----------------------------------------------------------------------

  it("calls API with the correct gameId", async () => {
    mockStartAnalysis.mockResolvedValueOnce(undefined);
    mockGetAnalysisStatus.mockResolvedValueOnce(makeStatus({ is_complete: true, percentage: 100 }));
    mockGetAnalysis.mockResolvedValueOnce(makeGameAnalysis());

    render(<AnalysisView gameId="test-game-42" />);

    await waitFor(() => {
      expect(screen.getByTestId("analysis-complete")).toBeInTheDocument();
    });

    expect(mockStartAnalysis).toHaveBeenCalledWith("test-game-42");
    expect(mockGetAnalysisStatus).toHaveBeenCalledWith("test-game-42");
    expect(mockGetAnalysis).toHaveBeenCalledWith("test-game-42");
  });
});
