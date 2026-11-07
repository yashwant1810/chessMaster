/**
 * Property 14: Critical Moment Detection
 *
 * **Validates: Requirements 11.3**
 *
 * For any sequence of centipawn evaluations for consecutive moves,
 * a distinct marker SHALL appear at position i if and only if the
 * absolute difference between the evaluation at position i and the
 * evaluation at position i−1 exceeds 100 centipawns.
 */
import * as fc from "fast-check";
import { describe, it, expect } from "vitest";
import {
  detectCriticalMoments,
  CRITICAL_THRESHOLD,
  type GraphDataPoint,
} from "../utils/evaluationGraph";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a clamped evaluation in [−2000, +2000]. */
const clampedEvalArb = fc.integer({ min: -2000, max: 2000 });

/**
 * Generates a sequence of GraphDataPoint objects with sequential moveIndex
 * values and random clamped evaluations.
 */
const dataPointsArb = (opts?: { minLength?: number; maxLength?: number }) =>
  fc
    .array(clampedEvalArb, {
      minLength: opts?.minLength ?? 0,
      maxLength: opts?.maxLength ?? 100,
    })
    .map((evals) =>
      evals.map(
        (clampedEval, i): GraphDataPoint => ({
          moveIndex: i,
          clampedEval,
          isCritical: false,
        }),
      ),
    );

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

describe("Property 14: Critical Moment Detection", () => {
  it("marks position i as critical iff |eval[i] − eval[i−1]| > 100", () => {
    fc.assert(
      fc.property(dataPointsArb({ minLength: 0, maxLength: 100 }), (dataPoints) => {
        const criticalSet = detectCriticalMoments(dataPoints);

        for (let i = 1; i < dataPoints.length; i++) {
          const diff = Math.abs(
            dataPoints[i].clampedEval - dataPoints[i - 1].clampedEval,
          );
          const isCritical = criticalSet.has(dataPoints[i].moveIndex);

          if (diff > CRITICAL_THRESHOLD) {
            expect(isCritical).toBe(true);
          } else {
            expect(isCritical).toBe(false);
          }
        }
      }),
      { numRuns: 200 },
    );
  });

  it("never marks the first position as critical", () => {
    fc.assert(
      fc.property(dataPointsArb({ minLength: 1, maxLength: 50 }), (dataPoints) => {
        const criticalSet = detectCriticalMoments(dataPoints);
        expect(criticalSet.has(dataPoints[0].moveIndex)).toBe(false);
      }),
      { numRuns: 200 },
    );
  });

  it("returns an empty set for sequences with 0 or 1 data points", () => {
    fc.assert(
      fc.property(dataPointsArb({ minLength: 0, maxLength: 1 }), (dataPoints) => {
        const criticalSet = detectCriticalMoments(dataPoints);
        expect(criticalSet.size).toBe(0);
      }),
      { numRuns: 100 },
    );
  });

  it("critical set contains only moveIndex values from the input", () => {
    fc.assert(
      fc.property(dataPointsArb({ minLength: 0, maxLength: 100 }), (dataPoints) => {
        const criticalSet = detectCriticalMoments(dataPoints);
        const allMoveIndices = new Set(dataPoints.map((dp) => dp.moveIndex));

        for (const idx of criticalSet) {
          expect(allMoveIndices.has(idx)).toBe(true);
        }
      }),
      { numRuns: 100 },
    );
  });
});
