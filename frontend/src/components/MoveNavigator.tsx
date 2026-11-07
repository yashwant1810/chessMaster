import { useEffect, useRef, useState } from "react";

export interface MoveNavigatorProps {
  currentMove: number;
  totalMoves: number;
  onNavigate: (moveIndex: number) => void;
  insightIndices?: Set<number>;
}

export default function MoveNavigator({ currentMove, totalMoves, onNavigate, insightIndices }: MoveNavigatorProps) {
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moveRef = useRef(currentMove);
  moveRef.current = currentMove;

  const isAtStart = currentMove <= 0;
  const isAtEnd = currentMove >= totalMoves;

  // Find previous/next insight from current position
  const goPrevInsight = () => {
    if (!insightIndices || insightIndices.size === 0) { onNavigate(0); return; }
    for (let i = currentMove - 1; i >= 0; i--) { if (insightIndices.has(i)) { setPlaying(false); onNavigate(i); return; } }
    onNavigate(0);
  };
  const goNextInsight = () => {
    if (!insightIndices || insightIndices.size === 0) { onNavigate(totalMoves); return; }
    for (let i = currentMove + 1; i <= totalMoves; i++) { if (insightIndices.has(i)) { setPlaying(false); onNavigate(i); return; } }
    onNavigate(totalMoves);
  };

  // Auto-play
  useEffect(() => {
    if (!playing) return;
    function step() {
      const next = moveRef.current + 1;
      if (next > totalMoves) { setPlaying(false); return; }
      onNavigate(next);
      if (insightIndices?.has(next)) { setPlaying(false); return; }
      timerRef.current = setTimeout(step, 1000);
    }
    timerRef.current = setTimeout(step, 800);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, totalMoves, onNavigate, insightIndices]);

  useEffect(() => { if (isAtEnd && playing) setPlaying(false); }, [isAtEnd, playing]);

  // Keyboard
  useEffect(() => {
    const stop = () => { setPlaying(false); if (timerRef.current) clearTimeout(timerRef.current); };
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") { e.preventDefault(); stop(); if (moveRef.current > 0) onNavigate(moveRef.current - 1); }
      else if (e.key === "ArrowRight") { e.preventDefault(); stop(); if (moveRef.current < totalMoves) onNavigate(moveRef.current + 1); }
      else if (e.key === " ") { e.preventDefault(); setPlaying(p => !p); }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [totalMoves, onNavigate]);

  const stop = () => { setPlaying(false); if (timerRef.current) clearTimeout(timerRef.current); };

  return (
    <nav className="move-nav">
      <button className="nav-btn" onClick={() => { stop(); goPrevInsight(); }} disabled={isAtStart} title="Previous insight (⏮)">⏮</button>
      <button className="nav-btn" onClick={() => { stop(); if (!isAtStart) onNavigate(currentMove - 1); }} disabled={isAtStart} title="Previous move (←)">‹</button>
      <button className={`nav-btn nav-btn--play ${playing ? "nav-btn--playing" : ""}`} onClick={() => setPlaying(p => !p)} title="Auto-play / Pause (Space)">
        {playing ? "⏸" : "▶"}
      </button>
      <button className="nav-btn" onClick={() => { stop(); if (!isAtEnd) onNavigate(currentMove + 1); }} disabled={isAtEnd} title="Next move (→)">›</button>
      <button className="nav-btn" onClick={() => { stop(); goNextInsight(); }} disabled={isAtEnd} title="Next insight (⏭)">⏭</button>
      <span className="nav-count">{currentMove} / {totalMoves}</span>
    </nav>
  );
}
