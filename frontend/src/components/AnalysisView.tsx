import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type {
  GameAnalysis,
  AnalyzedMove,
  CandidateMove,
  LearningInsight,
} from "../types";
import type { EvalDataPoint } from "../utils/evaluationGraph";
import type { BestMoveHighlight } from "./ChessBoard";
import { api } from "../api/client";
import ChessBoard from "./ChessBoard";
import MoveNavigator from "./MoveNavigator";
import MoveList from "./MoveList";
import CandidateMoves from "./CandidateMoves";
import InsightPanel from "./InsightPanel";
import GameSummary from "./GameSummary";
import EvaluationGraph from "./EvaluationGraph";
import PerformanceGraph from "./PerformanceGraph";
import ProgressIndicator from "./ProgressIndicator";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Analysis lifecycle phases — never show progress and results together (Req 5.6). */
export type AnalysisPhase = "loading" | "analyzing" | "complete" | "error";

export interface AnalysisViewProps {
  gameId: string;
}

// ---------------------------------------------------------------------------
// Initial FEN (standard starting position)
// ---------------------------------------------------------------------------

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * AnalysisView — main container that composes all analysis sub-components.
 *
 * Lifecycle:
 * 1. On mount: calls `api.startAnalysis(gameId)` and subscribes to SSE progress.
 * 2. During analysis: shows ProgressIndicator with real-time percentage.
 * 3. On completion: fetches full results via `api.getAnalysis(gameId)` and
 *    atomically replaces progress with analysis-complete results.
 * 4. Synchronizes `currentMoveIndex` across all child components.
 *
 * Requirements: 5.5, 5.6, 10.1
 */
export default function AnalysisView({ gameId }: AnalysisViewProps) {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  const [phase, setPhase] = useState<AnalysisPhase>("loading");
  const [progress, setProgress] = useState(0);
  const [analysis, setAnalysis] = useState<GameAnalysis | null>(null);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Ref to track whether SSE subscription is still active (for cleanup)
  const sseRef = useRef<EventSource | null>(null);
  // Ref to prevent double-start in StrictMode
  const startedRef = useRef(false);

  // ---------------------------------------------------------------------------
  // Start analysis + SSE subscription on mount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    let cancelled = false;

    async function init() {
      try {
        // Attempt to start analysis (may return 409 if already running/done)
        try {
          await api.startAnalysis(gameId);
        } catch (err: unknown) {
          // 409 = already in progress or done — check status
          const isConflict =
            err !== null &&
            typeof err === "object" &&
            "status" in err &&
            (err as { status: number }).status === 409;
          if (!isConflict) throw err;
        }

        if (cancelled) return;

        // Check current status — may already be complete
        const status = await api.getAnalysisStatus(gameId);
        if (cancelled) return;

        if (status.is_complete) {
          // Already done — fetch results directly
          const results = await api.getAnalysis(gameId);
          if (!cancelled) {
            setAnalysis(results);
            setPhase("complete");
          }
          return;
        }

        // Analysis in progress — subscribe to SSE for updates
        setPhase("analyzing");
        setProgress(status.percentage);

        const sse = api.streamAnalysisProgress(gameId);
        sseRef.current = sse;

        sse.onmessage = async (event: MessageEvent) => {
          if (cancelled) return;

          try {
            const data = JSON.parse(event.data as string) as {
              percentage: number;
              is_complete: boolean;
            };

            setProgress(data.percentage);

            if (data.is_complete) {
              sse.close();
              sseRef.current = null;

              // Fetch full results and atomically switch to complete phase
              const results = await api.getAnalysis(gameId);
              if (!cancelled) {
                setAnalysis(results);
                setPhase("complete");
              }
            }
          } catch {
            // Ignore malformed SSE messages
          }
        };

        sse.onerror = () => {
          // The reconnecting EventSource in client.ts handles reconnection.
          // We only show an error if the connection closes permanently.
        };
      } catch (err: unknown) {
        if (!cancelled) {
          const message =
            err instanceof Error ? err.message : "Failed to start analysis";
          setErrorMessage(message);
          setPhase("error");
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [gameId]);

  // ---------------------------------------------------------------------------
  // Navigation callback
  // ---------------------------------------------------------------------------

  const handleNavigate = useCallback((index: number) => {
    setCurrentMoveIndex(index);
  }, []);

  // ---------------------------------------------------------------------------
  // Derived data from analysis + currentMoveIndex
  // ---------------------------------------------------------------------------

  const currentMove: AnalyzedMove | null = useMemo(
    () => analysis?.moves[currentMoveIndex] ?? null,
    [analysis, currentMoveIndex],
  );

  /** FEN for the current position. */
  const currentFen: string = useMemo(() => {
    if (!currentMove) return STARTING_FEN;
    return currentMove.position_after;
  }, [currentMove]);

  /** Evaluation for the current position (after the current move). */
  const currentEvaluation: number | null = useMemo(() => {
    if (!currentMove) return null;
    return currentMove.evaluation_after.evaluation;
  }, [currentMove]);

  /** Mate-in for the current position. */
  const currentMateIn: number | null = useMemo(() => {
    if (!currentMove) return null;
    return currentMove.evaluation_after.mate_in;
  }, [currentMove]);

  /** Best move highlight: show when the player's move differs from top candidate. */
  const bestMoveHighlight: BestMoveHighlight | null = useMemo(() => {
    if (!currentMove || currentMove.candidate_moves.length === 0) return null;

    const topCandidate = currentMove.candidate_moves[0];
    if (topCandidate.move_san === currentMove.move_san) return null;

    // We need origin/destination squares. CandidateMove only has SAN,
    // so we cannot derive precise squares without a chess engine.
    // The ChessBoard component expects algebraic square coordinates.
    // Since the design stores SAN only, we skip highlighting when we
    // can't determine squares. In a complete integration the backend
    // would supply UCI notation (e.g. "e2e4") for candidate moves.
    return null;
  }, [currentMove]);

  /** Candidate moves for the current position. */
  const candidateMoves: CandidateMove[] = useMemo(
    () => currentMove?.candidate_moves ?? [],
    [currentMove],
  );

  /** Player's move evaluation for CandidateMoves component. */
  const playerEvaluation: number | null = useMemo(
    () => currentMove?.evaluation_after.evaluation ?? null,
    [currentMove],
  );

  const playerMateIn: number | null = useMemo(
    () => currentMove?.evaluation_after.mate_in ?? null,
    [currentMove],
  );

  /** Insight for the current move (null if best/excellent/good). */
  const currentInsight: LearningInsight | null = useMemo(
    () => currentMove?.insight ?? null,
    [currentMove],
  );

  /** Evaluation data points for the EvaluationGraph. */
  const evaluationDataPoints: EvalDataPoint[] = useMemo(() => {
    if (!analysis) return [];
    return analysis.moves.map((move, index) => ({
      moveIndex: index,
      evaluation: move.evaluation_after.evaluation,
      mateIn: move.evaluation_after.mate_in,
    }));
  }, [analysis]);

  /** Performance ratings for the PerformanceGraph. */
  const whiteRatings: number[] = useMemo(
    () => analysis?.white_summary.performance_ratings ?? [],
    [analysis],
  );

  const blackRatings: number[] = useMemo(
    () => analysis?.black_summary.performance_ratings ?? [],
    [analysis],
  );

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  // Phase: loading (initial)
  if (phase === "loading") {
    return (
      <div className="analysis-view" data-testid="analysis-view">
        <div className="analysis-view__loading" data-testid="analysis-loading">
          Loading analysis…
        </div>
      </div>
    );
  }

  // Phase: error
  if (phase === "error") {
    return (
      <div className="analysis-view" data-testid="analysis-view">
        <div className="analysis-view__error" data-testid="analysis-error">
          {errorMessage ?? "An error occurred"}
        </div>
      </div>
    );
  }

  // Phase: analyzing — show ProgressIndicator ONLY (Req 5.6: never show both)
  if (phase === "analyzing") {
    return (
      <div className="analysis-view" data-testid="analysis-view">
        <ProgressIndicator progress={progress} type="analysis" />
      </div>
    );
  }

  // Phase: complete — show all analysis components (no ProgressIndicator)
  const totalMoves = analysis ? analysis.moves.length : 0;

  return (
    <div className="analysis-view" data-testid="analysis-view">
      <div className="analysis-view__complete" data-testid="analysis-complete">
        {/* Board + evaluation bar (composed inside ChessBoard) */}
        <div className="analysis-view__board-section">
          <ChessBoard
            fen={currentFen}
            bestMove={bestMoveHighlight}
            evaluation={currentEvaluation}
            mateIn={currentMateIn}
          />
          <MoveNavigator
            currentMove={currentMoveIndex}
            totalMoves={totalMoves}
            onNavigate={handleNavigate}
          />
        </div>

        {/* Move list + candidate moves + insight panel */}
        <div className="analysis-view__moves-section">
          <MoveList
            moves={analysis?.moves ?? []}
            currentMove={currentMoveIndex}
            onSelect={handleNavigate}
          />
          <CandidateMoves
            candidates={candidateMoves}
            playerMove={currentMove?.move_san ?? ""}
            playerEvaluation={playerEvaluation}
            playerMateIn={playerMateIn}
          />
          <InsightPanel insight={currentInsight} />
        </div>

        {/* Graphs + summary */}
        <div className="analysis-view__details-section">
          <EvaluationGraph
            evaluations={evaluationDataPoints}
            currentMove={currentMoveIndex}
            onClick={handleNavigate}
          />
          <PerformanceGraph
            whiteRatings={whiteRatings}
            blackRatings={blackRatings}
            currentMove={currentMoveIndex}
          />
          <GameSummary
            whiteSummary={analysis?.white_summary ?? null}
            blackSummary={analysis?.black_summary ?? null}
            whitePlayer="White"
            blackPlayer="Black"
          />
        </div>
      </div>
    </div>
  );
}
