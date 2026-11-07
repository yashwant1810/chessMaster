import "./AnalysisView.css";
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type { GameAnalysis, AnalyzedMove } from "../types";
import type { EvalDataPoint } from "../utils/evaluationGraph";
import { api } from "../api/client";
import { playSoundForMove } from "../utils/sounds";
import CatCoach from "./CatCoach";
import ChessBoard from "./ChessBoard";
import MoveNavigator from "./MoveNavigator";
import MoveList from "./MoveList";
import CandidateMoves from "./CandidateMoves";
import GameSummary from "./GameSummary";
import EvaluationGraph from "./EvaluationGraph";
import PerformanceGraph from "./PerformanceGraph";
import ProgressIndicator from "./ProgressIndicator";

export type AnalysisPhase = "loading" | "analyzing" | "complete" | "error";
export interface AnalysisViewProps { gameId: string; username?: string; }

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

export default function AnalysisView({ gameId, username: _username }: AnalysisViewProps) {
  const [phase, setPhase] = useState<AnalysisPhase>("loading");
  const [progress, setProgress] = useState(0);
  const [analysis, setAnalysis] = useState<GameAnalysis | null>(null);
  const [currentMoveIndex, setCurrentMoveIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const sseRef = useRef<EventSource | null>(null);
  const startedRef = useRef(false);

  // Determine board orientation from username

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    let cancelled = false;

    async function init() {
      try {
        try { await api.startAnalysis(gameId); } catch (err: unknown) {
          const isConflict = err !== null && typeof err === "object" && "status" in err && (err as {status:number}).status === 409;
          if (!isConflict) throw err;
        }
        if (cancelled) return;
        const status = await api.getAnalysisStatus(gameId);
        if (cancelled) return;
        if (status.is_complete) {
          const results = await api.getAnalysis(gameId);
          if (!cancelled) { setAnalysis(results); setPhase("complete"); }
          return;
        }
        setPhase("analyzing"); setProgress(status.percentage);
        const sse = api.streamAnalysisProgress(gameId);
        sseRef.current = sse;
        sse.onmessage = async (event: MessageEvent) => {
          if (cancelled) return;
          try {
            const data = JSON.parse(event.data as string);
            setProgress(data.percentage);
            if (data.is_complete || data.type === "complete") {
              sse.close(); sseRef.current = null;
              const results = await api.getAnalysis(gameId);
              if (!cancelled) { setAnalysis(results); setPhase("complete"); }
            }
          } catch {}
        };
      } catch (err: unknown) {
        if (!cancelled) { setErrorMessage(err instanceof Error ? err.message : "Failed to start analysis"); setPhase("error"); }
      }
    }
    init();
    return () => { cancelled = true; if (sseRef.current) { sseRef.current.close(); sseRef.current = null; } };
  }, [gameId]);

  const handleNavigate = useCallback((index: number) => setCurrentMoveIndex(index), []);

  // Play sound when move changes
  const prevMoveRef = useRef(currentMoveIndex);
  useEffect(() => {
    if (prevMoveRef.current !== currentMoveIndex && analysis) {
      const move = analysis.moves[currentMoveIndex];
      if (move) playSoundForMove(move.move_san);
    }
    prevMoveRef.current = currentMoveIndex;
  }, [currentMoveIndex, analysis]);

  const currentMove: AnalyzedMove | null = useMemo(() => analysis?.moves[currentMoveIndex] ?? null, [analysis, currentMoveIndex]);
  const currentFen = useMemo(() => currentMove?.position_after ?? STARTING_FEN, [currentMove]);
  const currentEval = useMemo(() => currentMove?.evaluation_after?.evaluation ?? null, [currentMove]);
  const currentMateIn = useMemo(() => currentMove?.evaluation_after?.mate_in ?? null, [currentMove]);
  const candidateMoves = useMemo(() => currentMove?.candidate_moves ?? [], [currentMove]);
  const playerEval = useMemo(() => currentMove?.evaluation_after?.evaluation ?? null, [currentMove]);
  const playerMateIn = useMemo(() => currentMove?.evaluation_after?.mate_in ?? null, [currentMove]);
  const currentInsight = useMemo(() => currentMove?.insight ?? null, [currentMove]);
  const totalMoves = analysis ? analysis.moves.length - 1 : 0;

  const insightIndices = useMemo(() => {
    if (!analysis) return new Set<number>();
    const s = new Set<number>();
    analysis.moves.forEach((m, i) => { if (m.insight) s.add(i); });
    return s;
  }, [analysis]);

  const evaluationDataPoints: EvalDataPoint[] = useMemo(() => {
    if (!analysis) return [];
    return analysis.moves.map((m, i) => ({ moveIndex: i, evaluation: m.evaluation_after?.evaluation ?? null, mateIn: m.evaluation_after?.mate_in ?? null }));
  }, [analysis]);

  const whiteRatings = useMemo(() => analysis?.white_summary?.performance_ratings ?? [], [analysis]);
  const blackRatings = useMemo(() => analysis?.black_summary?.performance_ratings ?? [], [analysis]);

  if (phase === "loading") return <div className="av"><div className="av__status">Loading analysis…</div></div>;
  if (phase === "error") return <div className="av"><div className="av__status av__status--err">{errorMessage}</div></div>;
  if (phase === "analyzing") return <div className="av"><ProgressIndicator progress={progress} type="analysis" /></div>;

  return (
    <div className="av">
      {/* ROW 1: Board + Moves Panel — same height */}
      <div className="av__top">
        <div className="av__board-col">
          <ChessBoard fen={currentFen} bestMove={null} evaluation={currentEval} mateIn={currentMateIn} boardWidth={680} />
          <MoveNavigator currentMove={currentMoveIndex} totalMoves={totalMoves} onNavigate={handleNavigate} insightIndices={insightIndices} />
        </div>
        <div className="av__moves-col">
          <MoveList moves={analysis?.moves ?? []} currentMove={currentMoveIndex} onSelect={handleNavigate} />
        </div>
      </div>

      {/* ROW 2: Insight + Candidates — full width */}
      <div className="av__middle">
        <div className="av__insight-col">
          <CatCoach insight={currentInsight} />
        </div>
        <div className="av__cand-col">
          <CandidateMoves candidates={candidateMoves} playerMove={currentMove?.move_san ?? ""} playerEvaluation={playerEval} playerMateIn={playerMateIn} />
        </div>
      </div>

      {/* ROW 3: Eval graph */}
      <div className="av__section">
        <EvaluationGraph evaluations={evaluationDataPoints} currentMove={currentMoveIndex} onClick={handleNavigate} />
      </div>

      {/* ROW 4: Summary + Perf graph */}
      <div className="av__bottom">
        <div className="av__section">
          <GameSummary whiteSummary={analysis?.white_summary ?? null} blackSummary={analysis?.black_summary ?? null} whitePlayer="White" blackPlayer="Black" />
        </div>
        <div className="av__section">
          <PerformanceGraph whiteRatings={whiteRatings} blackRatings={blackRatings} currentMove={currentMoveIndex} />
        </div>
      </div>
    </div>
  );
}
