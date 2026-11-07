/**
 * Pure utility functions for the EvaluationGraph component.
 *
 * Extracted so tasks 10.3, 10.4, 10.5 can property-test clamping,
 * critical moment detection, and gap handling independently of React.
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Maximum centipawn magnitude displayed on the evaluation graph. */
export const MAX_EVAL = 2000;

/** Centipawn change threshold that marks a critical moment. */
export const CRITICAL_THRESHOLD = 100;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Raw evaluation data for a single half-move. */
export interface EvalDataPoint {
  moveIndex: number; // half-move index (0-based)
  evaluation: number | null; // centipawns, null if unavailable
  mateIn: number | null;
}

/** Processed data point ready for Recharts rendering. */
export interface GraphDataPoint {
  moveIndex: number;
  clampedEval: number;
  isCritical: boolean;
}

// ---------------------------------------------------------------------------
// Clamping (Property 13 — Requirement 11.1)
// ---------------------------------------------------------------------------

/**
 * Clamp a centipawn evaluation to [−2000, +2000].
 *
 * - Mate-in-N evaluations are represented at the ±2000 boundary
 *   (positive for White mate, negative for Black mate).
 * - Null evaluations return null (unavailable data).
 */
export function clampEvaluation(
  evaluation: number | null,
  mateIn: number | null,
): number | null {
  if (mateIn !== null && mateIn !== undefined) {
    return mateIn > 0 ? MAX_EVAL : -MAX_EVAL;
  }
  if (evaluation === null || evaluation === undefined) {
    return null;
  }
  return Math.max(-MAX_EVAL, Math.min(MAX_EVAL, evaluation));
}

// ---------------------------------------------------------------------------
// Critical Moment Detection (Property 14 — Requirement 11.3)
// ---------------------------------------------------------------------------

/**
 * Detect critical moments in a sequence of evaluated data points.
 *
 * A critical moment occurs at position i when the absolute difference
 * between the **clamped** evaluation at position i and the clamped
 * evaluation at position i−1 exceeds 100 centipawns.
 *
 * Only consecutive positions that both have available (non-null) clamped
 * evaluations are compared. The first position in the sequence is never
 * a critical moment (it has no predecessor to compare against).
 *
 * @returns A `Set` of `moveIndex` values that are critical moments.
 */
export function detectCriticalMoments(
  dataPoints: readonly GraphDataPoint[],
): Set<number> {
  const critical = new Set<number>();
  for (let i = 1; i < dataPoints.length; i++) {
    const prev = dataPoints[i - 1];
    const curr = dataPoints[i];
    if (
      Math.abs(curr.clampedEval - prev.clampedEval) > CRITICAL_THRESHOLD
    ) {
      critical.add(curr.moveIndex);
    }
  }
  return critical;
}

// ---------------------------------------------------------------------------
// Gap Handling / Graph Data Preparation (Property 15 — Requirement 11.5)
// ---------------------------------------------------------------------------

/**
 * Prepare graph-ready data from raw evaluation points.
 *
 * - Positions with unavailable evaluation data (null) are omitted.
 * - Remaining positions are kept in order, preserving the moveIndex
 *   on the X-axis so the graph accurately reflects move numbers.
 * - Critical moments are detected on the filtered, clamped sequence.
 *
 * @returns An array of `GraphDataPoint` objects ready for Recharts.
 */
export function prepareGraphData(
  evaluations: readonly EvalDataPoint[],
): GraphDataPoint[] {
  // Step 1: clamp values and filter out unavailable positions
  const evaluated: GraphDataPoint[] = [];
  for (const pt of evaluations) {
    const clamped = clampEvaluation(pt.evaluation, pt.mateIn);
    if (clamped !== null) {
      evaluated.push({
        moveIndex: pt.moveIndex,
        clampedEval: clamped,
        isCritical: false, // will be set in step 2
      });
    }
  }

  // Step 2: detect critical moments on the filtered sequence
  const criticalSet = detectCriticalMoments(evaluated);
  for (const pt of evaluated) {
    pt.isCritical = criticalSet.has(pt.moveIndex);
  }

  return evaluated;
}

// ---------------------------------------------------------------------------
// Click → move index mapping (Requirement 11.2)
// ---------------------------------------------------------------------------

/**
 * Given a clicked X coordinate, find the nearest moveIndex in the graph data.
 *
 * When the user clicks on the graph, Recharts provides the closest active
 * data point. This helper ensures we map that to the correct moveIndex.
 * If `dataPoints` is empty, returns -1.
 */
export function findNearestMoveIndex(
  dataPoints: readonly GraphDataPoint[],
  targetMoveIndex: number,
): number {
  if (dataPoints.length === 0) return -1;

  let nearest = dataPoints[0].moveIndex;
  let minDist = Math.abs(dataPoints[0].moveIndex - targetMoveIndex);

  for (let i = 1; i < dataPoints.length; i++) {
    const dist = Math.abs(dataPoints[i].moveIndex - targetMoveIndex);
    if (dist < minDist) {
      minDist = dist;
      nearest = dataPoints[i].moveIndex;
    }
  }

  return nearest;
}
