/**
 * Property 15: Evaluation Graph Gap Handling
 *
 * **Validates: Requirements 11.5**
 *
 * For any sequence of position evaluations where one or more positions have
 * unavailable evaluation data, the evaluation graph SHALL omit the unavailable
 * positions and connect the nearest positions that have evaluation data,
 * preserving the correct move-number mapping on the X-axis for all included
 * points.
 */
import * as fc from "fast-check";
import { describe, it, expect } from "vitest";
import {
  prepareGraphData,
  MAX_EVAL,
  type EvalDataPoint,
} from "../utils/evaluationGraph";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a non-null evaluation (centipawn value). */
const evalValueArb: fc.Arbitrary<number> = fc.integer({
  min: -5000,
  max: 5000,
});

/** Generates a nullable mate-in-N value. */
const mateInArb: fc.Arbitrary<number | null> = fc.oneof(
  fc.constant(null),
  fc.integer({ min: -20, max: -1 }),
  fc.integer({ min: 1, max: 20 }),
);

/**
 * Generates a single EvalDataPoint that has evaluation data available.
 * Either evaluation is non-null, or mateIn is non-null (or both).
 */
const availablePointArb = (moveIndex: number): fc.Arbitrary<EvalDataPoint> =>
  fc.oneof(
    // Only centipawn evaluation
    evalValueArb.map((ev) => ({
      moveIndex,
      evaluation: ev,
      mateIn: null,
    })),
    // Only mate-in-N
    mateInArb
      .filter((m) => m !== null)
      .map((m) => ({
        moveIndex,
        evaluation: null,
        mateIn: m,
      })),
    // Both present (mateIn takes priority in clamp logic)
    fc.tuple(evalValueArb, mateInArb.filter((m) => m !== null)).map(
      ([ev, m]) => ({
        moveIndex,
        evaluation: ev,
        mateIn: m,
      }),
    ),
  );

/**
 * Generates a single EvalDataPoint that is a gap (both evaluation and mateIn
 * are null — unavailable data).
 */
const gapPointArb = (moveIndex: number): fc.Arbitrary<EvalDataPoint> =>
  fc.constant({
    moveIndex,
    evaluation: null,
    mateIn: null,
  });

/**
 * Generates a random EvalDataPoint at a given moveIndex that is either
 * available or a gap.
 */
const anyPointArb = (moveIndex: number): fc.Arbitrary<EvalDataPoint> =>
  fc.oneof(availablePointArb(moveIndex), gapPointArb(moveIndex));

/**
 * Generates an array of EvalDataPoints with sequential moveIndexes, containing
 * a random mix of available evaluations and null gaps.
 */
const evalSequenceArb: fc.Arbitrary<EvalDataPoint[]> = fc
  .integer({ min: 0, max: 80 })
  .chain((len) => {
    if (len === 0) return fc.constant([]);
    const arbs = Array.from({ length: len }, (_, i) => anyPointArb(i));
    return fc.tuple(...arbs).map((pts) => pts as EvalDataPoint[]);
  });

/**
 * Generates a sequence that is guaranteed to have at least one gap.
 */
const sequenceWithGapsArb: fc.Arbitrary<EvalDataPoint[]> = fc
  .integer({ min: 2, max: 60 })
  .chain((len) => {
    // Pick at least one index to be a gap
    return fc
      .integer({ min: 0, max: len - 1 })
      .chain((gapIdx) => {
        const arbs = Array.from({ length: len }, (_, i) =>
          i === gapIdx ? gapPointArb(i) : anyPointArb(i),
        );
        return fc.tuple(...arbs).map((pts) => pts as EvalDataPoint[]);
      });
  });

// ---------------------------------------------------------------------------
// Helper: check if a point is "available" (has data)
// ---------------------------------------------------------------------------

function isAvailable(pt: EvalDataPoint): boolean {
  return pt.evaluation !== null || pt.mateIn !== null;
}

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

describe("Property 15: Evaluation Graph Gap Handling", () => {
  it("omits unavailable positions from the output", () => {
    fc.assert(
      fc.property(evalSequenceArb, (evaluations) => {
        const result = prepareGraphData(evaluations);

        // Count how many input points are available
        const availableCount = evaluations.filter(isAvailable).length;
        expect(result).toHaveLength(availableCount);

        // Every output moveIndex must correspond to an available input point
        const availableIndices = new Set(
          evaluations.filter(isAvailable).map((pt) => pt.moveIndex),
        );
        for (const gpt of result) {
          expect(availableIndices.has(gpt.moveIndex)).toBe(true);
        }
      }),
      { numRuns: 200 },
    );
  });

  it("preserves move-number mapping on the X-axis", () => {
    fc.assert(
      fc.property(evalSequenceArb, (evaluations) => {
        const result = prepareGraphData(evaluations);

        // The moveIndex of each output point must match the original input's
        // moveIndex for that position
        const availablePoints = evaluations.filter(isAvailable);
        expect(result).toHaveLength(availablePoints.length);

        for (let i = 0; i < result.length; i++) {
          expect(result[i].moveIndex).toBe(availablePoints[i].moveIndex);
        }
      }),
      { numRuns: 200 },
    );
  });

  it("connects nearest evaluated positions (output is in order with no gaps in indices that were available)", () => {
    fc.assert(
      fc.property(sequenceWithGapsArb, (evaluations) => {
        const result = prepareGraphData(evaluations);

        // Output should be a contiguous subsequence of available positions
        // in the same relative order as the input — i.e. the output forms
        // a connected sequence from the first available to the last available.
        for (let i = 1; i < result.length; i++) {
          // Move indices are monotonically increasing (preserved ordering)
          expect(result[i].moveIndex).toBeGreaterThan(
            result[i - 1].moveIndex,
          );
        }

        // Verify that no available position was skipped
        const availableMoveIndices = evaluations
          .filter(isAvailable)
          .map((pt) => pt.moveIndex);
        const outputMoveIndices = result.map((pt) => pt.moveIndex);
        expect(outputMoveIndices).toEqual(availableMoveIndices);
      }),
      { numRuns: 200 },
    );
  });

  it("clamps all output values to [−2000, +2000]", () => {
    fc.assert(
      fc.property(evalSequenceArb, (evaluations) => {
        const result = prepareGraphData(evaluations);

        for (const pt of result) {
          expect(pt.clampedEval).toBeGreaterThanOrEqual(-MAX_EVAL);
          expect(pt.clampedEval).toBeLessThanOrEqual(MAX_EVAL);
        }
      }),
      { numRuns: 200 },
    );
  });

  it("returns empty array for all-gap input", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 40 }).chain((len) => {
          const arbs = Array.from({ length: len }, (_, i) => gapPointArb(i));
          return fc.tuple(...arbs).map((pts) => pts as EvalDataPoint[]);
        }),
        (evaluations) => {
          const result = prepareGraphData(evaluations);
          expect(result).toHaveLength(0);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("returns empty array for empty input", () => {
    const result = prepareGraphData([]);
    expect(result).toHaveLength(0);
  });
});
