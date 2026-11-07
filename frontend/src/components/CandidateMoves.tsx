import type { CandidateMove } from "../types";
import {
  formatEvaluation,
  prepareDisplayCandidates,
  isPlayerMoveInCandidates,
} from "../utils/candidateMoves";
import "./CandidateMoves.css";

export interface CandidateMovesProps {
  /** Up to 3 candidate moves from Stockfish. */
  candidates: CandidateMove[];
  /** SAN notation of the player's actual move. */
  playerMove: string;
  /** Centipawn evaluation of the player's actual move (null if unavailable). */
  playerEvaluation: number | null;
  /** Mate-in-N for the player's actual move (null if not a mating line). */
  playerMateIn: number | null;
}

/**
 * Displays up to 3 candidate moves in descending evaluation order
 * alongside the player's actual move.
 *
 * - Shows centipawn evaluation for each candidate (Requirement 7.3).
 * - Visually marks the player's move if it appears in the candidate list
 *   (Requirement 7.4).
 * - Displays fewer candidates when position has fewer than 3 legal moves
 *   (Requirement 7.1).
 * - Always shows the player's actual move with its evaluation below
 *   the candidate list, unless the player's move is already among the
 *   candidates.
 */
export default function CandidateMoves({
  candidates,
  playerMove,
  playerEvaluation,
  playerMateIn,
}: CandidateMovesProps) {
  const displayCandidates = prepareDisplayCandidates(candidates, playerMove);
  const playerInCandidates = isPlayerMoveInCandidates(
    playerMove,
    displayCandidates.map((dc) => ({
      move_san: dc.move_san,
      evaluation: null,
      mate_in: null,
    })),
  );

  if (displayCandidates.length === 0) {
    return (
      <div className="candidate-moves" data-testid="candidate-moves">
        <h3 className="candidate-moves-title">Candidate Moves</h3>
        <p className="candidate-moves-empty" data-testid="candidate-moves-empty">
          No candidate moves available.
        </p>
      </div>
    );
  }

  return (
    <div className="candidate-moves" data-testid="candidate-moves">
      <h3 className="candidate-moves-title">Candidate Moves</h3>

      <ol className="candidate-moves-list" data-testid="candidate-moves-list">
        {displayCandidates.map((dc, i) => (
          <li
            key={dc.move_san}
            className={`candidate-move-item${dc.isPlayerMove ? " candidate-move-item--player" : ""}`}
            data-testid={`candidate-move-${i}`}
          >
            <span className="candidate-move-rank" aria-hidden="true">
              {i + 1}
            </span>
            <span className="candidate-move-san">{dc.move_san}</span>
            <span className="candidate-move-eval" data-testid={`candidate-eval-${i}`}>
              {dc.formattedEval}
            </span>
            {dc.isPlayerMove && (
              <span
                className="candidate-move-player-badge"
                data-testid={`candidate-player-badge-${i}`}
                aria-label="Player's move"
              >
                You
              </span>
            )}
          </li>
        ))}
      </ol>

      {/* Show player's move separately when it's NOT among the candidates */}
      {!playerInCandidates && (
        <div className="candidate-moves-player" data-testid="player-move-section">
          <div className="candidate-moves-player-label">Your move</div>
          <div className="candidate-moves-player-row" data-testid="player-move-row">
            <span className="candidate-moves-player-san">{playerMove}</span>
            <span
              className="candidate-moves-player-eval"
              data-testid="player-move-eval"
            >
              {formatEvaluation(playerEvaluation, playerMateIn)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
