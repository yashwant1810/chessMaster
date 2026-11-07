import { Chessboard } from "react-chessboard";
import EvaluationBar from "./EvaluationBar";
import "./ChessBoard.css";

/** Arrow type matching react-chessboard's internal Arrow shape. */
type Arrow = { startSquare: string; endSquare: string; color: string };

/** Highlight colors */
const BEST_MOVE_HIGHLIGHT = "rgba(0, 120, 215, 0.45)"; // blue tint for best move squares
const BEST_MOVE_ARROW_COLOR = "rgba(0, 120, 215, 0.7)"; // blue arrow for best move

export interface BestMoveHighlight {
  /** Origin square of the best move in algebraic notation (e.g. "e2"). */
  from: string;
  /** Destination square of the best move in algebraic notation (e.g. "e4"). */
  to: string;
}

export interface ChessBoardProps {
  /** FEN string describing the current board position. */
  fen: string;
  /**
   * Best move to highlight when the player's move differs from the top
   * candidate. Pass `null` when no best-move highlight is needed.
   */
  bestMove: BestMoveHighlight | null;
  /** Centipawn evaluation from White's perspective. */
  evaluation: number | null;
  /** Mate-in-N indicator (positive = White mates, negative = Black mates). */
  mateIn: number | null;
  /** Board width in pixels. Defaults to 560. */
  boardWidth?: number;
}

/**
 * ChessBoard — renders an 8×8 board with react-chessboard and an
 * adjacent EvaluationBar.
 *
 * - Displays visually distinct pieces for all 6 types in both colors
 *   (handled natively by react-chessboard's default SVG pieces).
 * - Highlights the top candidate move's origin/destination squares with
 *   a distinct blue tint when the player's move differs from the best move.
 *
 * @see Requirements 7.2, 10.1, 10.5, 10.6
 */
export default function ChessBoard({
  fen,
  bestMove,
  evaluation,
  mateIn,
  boardWidth = 560,
}: ChessBoardProps) {
  // Build square highlight styles for the best move
  const squareStyles: Record<string, React.CSSProperties> = {};
  if (bestMove) {
    squareStyles[bestMove.from] = { backgroundColor: BEST_MOVE_HIGHLIGHT };
    squareStyles[bestMove.to] = { backgroundColor: BEST_MOVE_HIGHLIGHT };
  }

  // Build arrows for best move
  const arrows: Arrow[] = [];
  if (bestMove) {
    arrows.push({
      startSquare: bestMove.from,
      endSquare: bestMove.to,
      color: BEST_MOVE_ARROW_COLOR,
    });
  }

  return (
    <div className="chess-board-container" data-testid="chess-board-container">
      <EvaluationBar
        evaluation={evaluation}
        mateIn={mateIn}
        height={boardWidth}
      />
      <div
        className="chess-board-wrapper"
        data-testid="chess-board"
        style={{ width: boardWidth, height: boardWidth }}
      >
        <Chessboard
          options={{
            id: "analysis-board",
            position: fen,
            squareStyles,
            arrows,
            allowDragging: false,
            allowDrawingArrows: false,
            showAnimations: true,
            animationDurationInMs: 200,
            boardStyle: {
              borderRadius: "4px",
              boxShadow: "0 2px 10px rgba(0, 0, 0, 0.15)",
            },
          }}
        />
      </div>
    </div>
  );
}
