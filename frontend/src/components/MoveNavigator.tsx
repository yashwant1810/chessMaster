import { useCallback, useEffect } from "react";

export interface MoveNavigatorProps {
  /** Current move index: 0 = initial position, totalMoves = last move. */
  currentMove: number;
  /** Total number of half-moves in the game. */
  totalMoves: number;
  /** Callback to navigate to a specific move index. */
  onNavigate: (moveIndex: number) => void;
}

/**
 * MoveNavigator — first/previous/next/last navigation controls with keyboard support.
 *
 * Requirements: 10.2, 10.3, 10.4, 10.7, 10.8
 */
export default function MoveNavigator({
  currentMove,
  totalMoves,
  onNavigate,
}: MoveNavigatorProps) {
  const isAtStart = currentMove <= 0;
  const isAtEnd = currentMove >= totalMoves;

  const goFirst = useCallback(() => {
    if (!isAtStart) onNavigate(0);
  }, [isAtStart, onNavigate]);

  const goPrevious = useCallback(() => {
    if (!isAtStart) onNavigate(currentMove - 1);
  }, [isAtStart, currentMove, onNavigate]);

  const goNext = useCallback(() => {
    if (!isAtEnd) onNavigate(currentMove + 1);
  }, [isAtEnd, currentMove, onNavigate]);

  const goLast = useCallback(() => {
    if (!isAtEnd) onNavigate(totalMoves);
  }, [isAtEnd, totalMoves, onNavigate]);

  // Global keyboard handler for left/right arrow keys
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        if (currentMove > 0) onNavigate(currentMove - 1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        if (currentMove < totalMoves) onNavigate(currentMove + 1);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [currentMove, totalMoves, onNavigate]);

  return (
    <nav
      className="move-navigator"
      aria-label="Move navigation"
      role="navigation"
    >
      <button
        className="move-navigator__btn"
        onClick={goFirst}
        disabled={isAtStart}
        aria-label="First move"
        title="First move"
      >
        ⏮
      </button>
      <button
        className="move-navigator__btn"
        onClick={goPrevious}
        disabled={isAtStart}
        aria-label="Previous move"
        title="Previous move"
      >
        ◀
      </button>
      <button
        className="move-navigator__btn"
        onClick={goNext}
        disabled={isAtEnd}
        aria-label="Next move"
        title="Next move"
      >
        ▶
      </button>
      <button
        className="move-navigator__btn"
        onClick={goLast}
        disabled={isAtEnd}
        aria-label="Last move"
        title="Last move"
      >
        ⏭
      </button>
    </nav>
  );
}
