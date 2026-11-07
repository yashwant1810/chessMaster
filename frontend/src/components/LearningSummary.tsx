import { useCallback } from "react";
import type { LearningInsight } from "../types";
import "./LearningSummary.css";

export interface LearningSummaryProps {
  /** All insights from the game (inaccuracy/mistake/blunder moves only). */
  insights: LearningInsight[];
  /** Optional callback when the user clicks a move to navigate to it. */
  onMoveClick?: (moveNumber: number, isWhite: boolean) => void;
}

/**
 * CSS modifier for the item border-left color.
 */
const ITEM_CSS: Record<string, string> = {
  inaccuracy: "learning-summary-item--inaccuracy",
  mistake: "learning-summary-item--mistake",
  blunder: "learning-summary-item--blunder",
};

/**
 * CSS modifier for the classification badge.
 */
const BADGE_CSS: Record<string, string> = {
  inaccuracy: "learning-summary-badge--inaccuracy",
  mistake: "learning-summary-badge--mistake",
  blunder: "learning-summary-badge--blunder",
};

/**
 * Format a move identifier like "1. e4" or "1... e5".
 */
function formatMoveId(moveNumber: number, isWhite: boolean, moveSan: string): string {
  return isWhite
    ? `${moveNumber}. ${moveSan}`
    : `${moveNumber}... ${moveSan}`;
}

/**
 * Lists all suboptimal moves from the game analysis with their explanations.
 *
 * Each item shows:
 *   - Classification badge (inaccuracy / mistake / blunder)
 *   - Move identifier (e.g., "5. Nf3" or "12... Qd7")
 *   - Centipawn loss
 *   - Best move suggestion
 *   - Explanation text
 *
 * Clicking on a move calls `onMoveClick` so the parent can navigate
 * the board to that position.
 *
 * Requirements: 9.4 (learning summary listing all suboptimal moves with
 * explanations).
 */
export default function LearningSummary({
  insights,
  onMoveClick,
}: LearningSummaryProps) {
  const handleClick = useCallback(
    (moveNumber: number, isWhite: boolean) => () => {
      onMoveClick?.(moveNumber, isWhite);
    },
    [onMoveClick],
  );

  const handleKeyDown = useCallback(
    (moveNumber: number, isWhite: boolean) => (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onMoveClick?.(moveNumber, isWhite);
      }
    },
    [onMoveClick],
  );

  if (insights.length === 0) {
    return (
      <div className="learning-summary" data-testid="learning-summary">
        <h3 className="learning-summary-title">Learning Summary</h3>
        <p className="learning-summary-empty" data-testid="learning-summary-empty">
          No suboptimal moves found. Great game!
        </p>
      </div>
    );
  }

  return (
    <div className="learning-summary" data-testid="learning-summary">
      <h3 className="learning-summary-title">Learning Summary</h3>

      <ul className="learning-summary-list" data-testid="learning-summary-list">
        {insights.map((insight, index) => {
          const classification = insight.classification;
          const itemClass = ITEM_CSS[classification] ?? "";
          const badgeClass = BADGE_CSS[classification] ?? "";
          const moveLabel = formatMoveId(
            insight.move_number,
            insight.is_white,
            insight.played_move,
          );
          const isClickable = !!onMoveClick;

          return (
            <li
              key={`${insight.move_number}-${insight.is_white ? "w" : "b"}`}
              className={`learning-summary-item ${itemClass}${isClickable ? " learning-summary-item--clickable" : ""}`}
              data-testid={`learning-summary-item-${index}`}
              onClick={isClickable ? handleClick(insight.move_number, insight.is_white) : undefined}
              onKeyDown={isClickable ? handleKeyDown(insight.move_number, insight.is_white) : undefined}
              tabIndex={isClickable ? 0 : undefined}
              role={isClickable ? "button" : undefined}
            >
              <div className="learning-summary-item-header">
                <span
                  className={`learning-summary-badge ${badgeClass}`}
                  data-testid={`learning-summary-badge-${index}`}
                >
                  {classification}
                </span>
                <span
                  className="learning-summary-move-label"
                  data-testid={`learning-summary-move-${index}`}
                >
                  {moveLabel}
                </span>
                <span
                  className="learning-summary-cp-loss"
                  data-testid={`learning-summary-cp-loss-${index}`}
                >
                  −{insight.centipawn_loss} cp
                </span>
              </div>

              <div
                className="learning-summary-best-move"
                data-testid={`learning-summary-best-move-${index}`}
              >
                Best: {insight.best_move}
              </div>

              <div
                className="learning-summary-explanation"
                data-testid={`learning-summary-explanation-${index}`}
              >
                {insight.explanation}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
