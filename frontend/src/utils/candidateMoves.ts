import type { CandidateMove } from "../types";

/**
 * Pure utility functions for CandidateMoves display logic.
 *
 * Extracted so task 9.8 can property-test sorting and formatting
 * independently of the React component.
 */

/**
 * Sort candidate moves in descending order of evaluation.
 *
 * - Candidates with a `mate_in` value are ranked above all centipawn values
 *   when mate favours the side (positive = White mates = best for White).
 * - Null evaluations sort last.
 *
 * @returns A **new** sorted array — the input is never mutated.
 */
export function sortCandidatesByEval(
  candidates: readonly CandidateMove[],
): CandidateMove[] {
  return [...candidates].sort((a, b) => {
    const scoreA = effectiveScore(a);
    const scoreB = effectiveScore(b);
    return scoreB - scoreA; // descending
  });
}

/**
 * Compute an effective numeric score used for sorting only.
 *
 * Mate-in-N values are mapped to large magnitude numbers so they sort
 * above/below all centipawn values.  Null evaluations map to -Infinity
 * so they always appear last in descending order.
 */
export function effectiveScore(candidate: CandidateMove): number {
  if (candidate.mate_in !== null) {
    // Positive mate_in → White is mating → very high score
    // Negative mate_in → Black is mating → very low score
    // Closer mate is better, so we use inverse distance.
    return candidate.mate_in > 0
      ? 100_000 - candidate.mate_in
      : -100_000 - candidate.mate_in;
  }
  if (candidate.evaluation !== null) {
    return candidate.evaluation;
  }
  return -Infinity;
}

/**
 * Limit candidates to at most `maxCount` entries.
 *
 * When a position has fewer than `maxCount` legal moves, only the
 * available moves are returned (Requirement 7.1).
 */
export function limitCandidates(
  candidates: readonly CandidateMove[],
  maxCount: number = 3,
): CandidateMove[] {
  return candidates.slice(0, maxCount);
}

/**
 * Format a centipawn evaluation as a human-readable string.
 *
 * - Positive values are prefixed with "+".
 * - Mate-in-N shows as "M+N" or "M-N".
 * - Null evaluation shows as "–" (en-dash).
 */
export function formatEvaluation(
  evaluation: number | null,
  mateIn: number | null,
): string {
  if (mateIn !== null) {
    return mateIn > 0 ? `M+${mateIn}` : `M${mateIn}`;
  }
  if (evaluation !== null) {
    const sign = evaluation > 0 ? "+" : "";
    return `${sign}${evaluation}`;
  }
  return "–";
}

/**
 * Determine whether a player's move (SAN) appears in the candidate list.
 */
export function isPlayerMoveInCandidates(
  playerMove: string,
  candidates: readonly CandidateMove[],
): boolean {
  return candidates.some((c) => c.move_san === playerMove);
}

/**
 * Prepare the display-ready list of candidates: sorted descending,
 * limited to 3, with formatting metadata.
 */
export interface DisplayCandidate {
  move_san: string;
  formattedEval: string;
  isPlayerMove: boolean;
}

export function prepareDisplayCandidates(
  candidates: readonly CandidateMove[],
  playerMove: string,
): DisplayCandidate[] {
  const sorted = sortCandidatesByEval(candidates);
  const limited = limitCandidates(sorted, 3);
  return limited.map((c) => ({
    move_san: c.move_san,
    formattedEval: formatEvaluation(c.evaluation, c.mate_in),
    isPlayerMove: c.move_san === playerMove,
  }));
}
