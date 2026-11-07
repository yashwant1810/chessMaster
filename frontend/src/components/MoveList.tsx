import { useCallback } from "react";
import type { AnalyzedMove, MoveClassification } from "../types";
import "./MoveList.css";

export interface MoveListProps {
  moves: AnalyzedMove[];
  currentMove: number;
  onSelect: (moveIndex: number) => void;
}

/**
 * Classification → unique icon shape mapping.
 *
 * Each category uses a distinct Unicode symbol so that no two categories
 * share the same icon shape (Requirement 6.3).
 */
const CLASSIFICATION_ICONS: Record<MoveClassification, string> = {
  best: "★",
  excellent: "◆",
  good: "●",
  inaccuracy: "▲",
  mistake: "■",
  blunder: "✖",
};

/**
 * Classification → CSS modifier for color.
 */
const CLASSIFICATION_CSS: Record<MoveClassification, string> = {
  best: "classification-icon--best",
  excellent: "classification-icon--excellent",
  good: "classification-icon--good",
  inaccuracy: "classification-icon--inaccuracy",
  mistake: "classification-icon--mistake",
  blunder: "classification-icon--blunder",
};

/**
 * Renders the classification indicator for a single move.
 *
 * - When classification is present: shows a color-coded icon with the
 *   category's unique shape.
 * - When classification is null: shows a "?" unavailable indicator
 *   (Requirement 6.5).
 */
function ClassificationIndicator({
  classification,
}: {
  classification: MoveClassification | null;
}) {
  if (classification === null) {
    return (
      <span
        className="classification-unavailable"
        title="Classification unavailable"
        aria-label="Classification unavailable"
        data-testid="classification-unavailable"
      >
        ?
      </span>
    );
  }

  return (
    <span
      className={`classification-icon ${CLASSIFICATION_CSS[classification]}`}
      title={classification}
      aria-label={`${classification} move`}
      data-testid={`classification-${classification}`}
    >
      {CLASSIFICATION_ICONS[classification]}
    </span>
  );
}

/**
 * Groups half-moves into rows of (move_number, white_move, black_move).
 *
 * Each row contains the move number and up to two half-moves. The index
 * stored for each half-move is its position in the original `moves` array
 * so that `onSelect` receives the correct index.
 */
interface MoveRow {
  moveNumber: number;
  white: { move: AnalyzedMove; index: number } | null;
  black: { move: AnalyzedMove; index: number } | null;
}

function groupMovesIntoRows(moves: AnalyzedMove[]): MoveRow[] {
  const rowMap = new Map<number, MoveRow>();

  for (let i = 0; i < moves.length; i++) {
    const move = moves[i];
    const num = move.move_number;

    if (!rowMap.has(num)) {
      rowMap.set(num, { moveNumber: num, white: null, black: null });
    }

    const row = rowMap.get(num)!;
    if (move.is_white) {
      row.white = { move, index: i };
    } else {
      row.black = { move, index: i };
    }
  }

  return Array.from(rowMap.values()).sort(
    (a, b) => a.moveNumber - b.moveNumber,
  );
}

/**
 * Tabular move list with move number, White move, and Black move columns.
 *
 * Each move cell shows a color-coded classification icon and the SAN
 * notation. The currently active move is highlighted. Clicking a move
 * cell calls `onSelect` with the move's index in the `moves` array.
 *
 * When a move's classification is null the cell shows a "classification
 * unavailable" indicator (Requirement 6.5).
 */
export default function MoveList({
  moves,
  currentMove,
  onSelect,
}: MoveListProps) {
  const rows = groupMovesIntoRows(moves);

  const handleSelect = useCallback(
    (index: number) => () => onSelect(index),
    [onSelect],
  );

  const handleKeyDown = useCallback(
    (index: number) => (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onSelect(index);
      }
    },
    [onSelect],
  );

  if (moves.length === 0) {
    return (
      <div className="move-list-empty" data-testid="move-list-empty">
        No moves to display.
      </div>
    );
  }

  return (
    <div className="move-list-container" data-testid="move-list">
      <table className="move-list-table" role="grid" aria-label="Move list">
        <thead>
          <tr>
            <th className="move-list-header move-list-header-number">#</th>
            <th className="move-list-header">White</th>
            <th className="move-list-header">Black</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.moveNumber} className="move-list-row">
              <td className="move-list-cell move-list-cell-number">
                {row.moveNumber}
              </td>

              {/* White move cell */}
              {row.white ? (
                <td
                  className={`move-list-cell move-list-cell-move${row.white.index === currentMove ? " move-list-cell-move--active" : ""}`}
                  data-testid={`move-cell-${row.white.index}`}
                  onClick={handleSelect(row.white.index)}
                  onKeyDown={handleKeyDown(row.white.index)}
                  tabIndex={0}
                  role="gridcell"
                  aria-current={
                    row.white.index === currentMove ? "true" : undefined
                  }
                >
                  <span className="move-entry">
                    <ClassificationIndicator
                      classification={row.white.move.classification}
                    />
                    {row.white.move.move_san}
                  </span>
                </td>
              ) : (
                <td className="move-list-cell" />
              )}

              {/* Black move cell */}
              {row.black ? (
                <td
                  className={`move-list-cell move-list-cell-move${row.black.index === currentMove ? " move-list-cell-move--active" : ""}`}
                  data-testid={`move-cell-${row.black.index}`}
                  onClick={handleSelect(row.black.index)}
                  onKeyDown={handleKeyDown(row.black.index)}
                  tabIndex={0}
                  role="gridcell"
                  aria-current={
                    row.black.index === currentMove ? "true" : undefined
                  }
                >
                  <span className="move-entry">
                    <ClassificationIndicator
                      classification={row.black.move.classification}
                    />
                    {row.black.move.move_san}
                  </span>
                </td>
              ) : (
                <td className="move-list-cell" />
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
