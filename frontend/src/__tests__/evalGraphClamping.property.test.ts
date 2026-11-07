/**
 * Property 13: Evaluation Graph Clamping
 *
 * **Validates: Requirements 11.1**
 *
 * For any centipawn evaluation value, the evaluation graph SHALL display
 * it clamped to the range [−2000, +2000].
 * For any mate-in-N evaluation, the graph SHALL represent it at the ±2000
 * boundary (positive for White mate, negative for Black mate).
 */
import * as fc from "fast-check";
import { describe, it, expect } from "vitest";
import { clampEvaluation, MAX_EVAL } from "../utils/evaluationGraph";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Arbitrary integer evaluation (centipawns) spanning well beyond the clamp range. */
const evalArb = fc.integer({ min: -100_000, max: 100_000 });

/** Positive mate-in-N (White mates). */
const positiveMateArb = fc.integer({ min: 1, max: 200 });

/** Negative mate-in-N (Black mates). */
const negativeMateArb = fc.integer({ min: -200, max: -1 });

/** Any non-zero mate-in-N. */
const mateArb = fc.oneof(positiveMateArb, negativeMateArb);

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

describe("Property 13: Evaluation Graph Clamping", () => {
  it("centipawn evaluations are clamped to [−2000, +2000]", () => {
    fc.assert(
      fc.property(evalArb, (evaluation) => {
        const result = clampEvaluation(evaluation, null);

        expect(result).not.toBeNull();
        expect(result!).toBeGreaterThanOrEqual(-MAX_EVAL);
        expect(result!).toBeLessThanOrEqual(MAX_EVAL);
      }),
      { numRuns: 200 },
    );
  });

  it("clamped value equals original when within bounds", () => {
    const inBoundsArb = fc.integer({ min: -MAX_EVAL, max: MAX_EVAL });

    fc.assert(
      fc.property(inBoundsArb, (evaluation) => {
        const result = clampEvaluation(evaluation, null);
        expect(result).toBe(evaluation);
      }),
      { numRuns: 200 },
    );
  });

  it("positive mate-in-N evaluations are displayed at +2000 boundary", () => {
    fc.assert(
      fc.property(positiveMateArb, (mateIn) => {
        // evaluation can be any value or null — mateIn takes precedence
        const result = clampEvaluation(null, mateIn);
        expect(result).toBe(MAX_EVAL);
      }),
      { numRuns: 100 },
    );
  });

  it("negative mate-in-N evaluations are displayed at −2000 boundary", () => {
    fc.assert(
      fc.property(negativeMateArb, (mateIn) => {
        const result = clampEvaluation(null, mateIn);
        expect(result).toBe(-MAX_EVAL);
      }),
      { numRuns: 100 },
    );
  });

  it("mate-in-N takes precedence over centipawn evaluation", () => {
    fc.assert(
      fc.property(evalArb, mateArb, (evaluation, mateIn) => {
        const result = clampEvaluation(evaluation, mateIn);

        // When mateIn is provided, evaluation is irrelevant
        const expected = mateIn > 0 ? MAX_EVAL : -MAX_EVAL;
        expect(result).toBe(expected);
      }),
      { numRuns: 200 },
    );
  });

  it("null evaluation with null mateIn returns null", () => {
    const result = clampEvaluation(null, null);
    expect(result).toBeNull();
  });
});
