import type { LearningInsight, MoveClassification } from "../types";
import "./InsightPanel.css";

export interface InsightPanelProps {
  /** The insight for the current move, or null when the move is good/excellent/best. */
  insight: LearningInsight | null;
}

/**
 * CSS modifier for the classification badge.
 */
const BADGE_CSS: Record<string, string> = {
  inaccuracy: "insight-panel-badge--inaccuracy",
  mistake: "insight-panel-badge--mistake",
  blunder: "insight-panel-badge--blunder",
};

/**
 * Format a move identifier like "1. e4" or "1... e5".
 */
function formatMoveId(moveNumber: number, isWhite: boolean): string {
  return isWhite ? `${moveNumber}. ` : `${moveNumber}... `;
}

/**
 * Displays insight details for a suboptimal move (inaccuracy, mistake, blunder).
 *
 * Shows:
 *   - Classification badge (Requirement 9.3)
 *   - Centipawn loss (Requirement 9.1)
 *   - Best move in SAN (Requirement 9.2)
 *   - Principal variation line up to 5 moves (Requirement 9.2)
 *   - Textual explanation (Requirement 9.3)
 *
 * When `insight` is null (the current move is best/excellent/good), the
 * panel is cleared and shows a neutral message (Requirement 9.5).
 */
export default function InsightPanel({ insight }: InsightPanelProps) {
  if (!insight) {
    return (
      <div className="insight-panel" data-testid="insight-panel">
        <h3 className="insight-panel-title">Move Insight</h3>
        <p className="insight-panel-empty" data-testid="insight-panel-empty">
          No issues with this move.
        </p>
      </div>
    );
  }

  const classification = insight.classification as MoveClassification;
  const badgeClass = BADGE_CSS[classification] ?? "";
  const moveId = formatMoveId(insight.move_number, insight.is_white);

  return (
    <div className="insight-panel" data-testid="insight-panel">
      <h3 className="insight-panel-title">Move Insight</h3>

      <div className="insight-panel-content" data-testid="insight-panel-content">
        {/* Classification badge and move info */}
        <div className="insight-panel-move-info">
          <span
            className={`insight-panel-badge ${badgeClass}`}
            data-testid="insight-badge"
          >
            {classification}
          </span>
          <span className="insight-panel-move-label" data-testid="insight-move-id">
            {moveId}{insight.played_move}
          </span>
        </div>

        {/* Centipawn loss */}
        <div className="insight-panel-cp-loss" data-testid="insight-cp-loss">
          <span className="insight-panel-cp-loss-label">Centipawn loss:</span>
          <span className="insight-panel-cp-loss-value" data-testid="insight-cp-loss-value">
            {insight.centipawn_loss}
          </span>
        </div>

        {/* Best move */}
        <div className="insight-panel-best-move" data-testid="insight-best-move">
          <span className="insight-panel-best-move-label">Best move:</span>
          <span className="insight-panel-best-move-value" data-testid="insight-best-move-value">
            {insight.best_move}
          </span>
        </div>

        {/* Principal variation */}
        {insight.principal_variation.length > 0 && (
          <div className="insight-panel-pv" data-testid="insight-pv">
            <div className="insight-panel-pv-label">Principal variation:</div>
            <div className="insight-panel-pv-moves" data-testid="insight-pv-moves">
              {insight.principal_variation.join(" ")}
            </div>
          </div>
        )}

        {/* Explanation text */}
        <div className="insight-panel-explanation" data-testid="insight-explanation">
          {insight.explanation}
        </div>
      </div>
    </div>
  );
}
