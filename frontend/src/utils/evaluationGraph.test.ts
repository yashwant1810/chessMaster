import { describe, it, expect } from "vitest";
import {
  clampEvaluation,
  detectCriticalMoments,
  prepareGraphData,
  findNearestMoveIndex,
  MAX_EVAL,
  CRITICAL_THRESHOLD,
} from "./evaluationGraph";
import type { EvalDataPoint, GraphDataPoint } from "./evaluationGraph";

// -----------------------------------------------------------------------
// clampEvaluation
// -----------------------------------------------------------------------

describe("clampEvaluation", () => {
  it("returns null when both evaluation and mateIn are null", () => {
    expect(clampEvaluation(null, null)).toBeNull();
  });

  it("clamps positive evaluation to MAX_EVAL", () => {
    expect(clampEvaluation(3000, null)).toBe(MAX_EVAL);
  });

  it("clamps negative evaluation to -MAX_EVAL", () => {
    expect(clampEvaluation(-5000, null)).toBe(-MAX_EVAL);
  });

  it("passes through evaluation within range", () => {
    expect(clampEvaluation(500, null)).toBe(500);
    expect(clampEvaluation(-800, null)).toBe(-800);
    expect(clampEvaluation(0, null)).toBe(0);
  });

  it("maps positive mateIn to +MAX_EVAL", () => {
    expect(clampEvaluation(null, 3)).toBe(MAX_EVAL);
    expect(clampEvaluation(null, 1)).toBe(MAX_EVAL);
  });

  it("maps negative mateIn to -MAX_EVAL", () => {
    expect(clampEvaluation(null, -2)).toBe(-MAX_EVAL);
    expect(clampEvaluation(null, -5)).toBe(-MAX_EVAL);
  });

  it("mateIn takes precedence over evaluation", () => {
    expect(clampEvaluation(100, 2)).toBe(MAX_EVAL);
    expect(clampEvaluation(-100, -3)).toBe(-MAX_EVAL);
  });

  it("clamps exactly at boundary values", () => {
    expect(clampEvaluation(MAX_EVAL, null)).toBe(MAX_EVAL);
    expect(clampEvaluation(-MAX_EVAL, null)).toBe(-MAX_EVAL);
  });
});

// -----------------------------------------------------------------------
// detectCriticalMoments
// -----------------------------------------------------------------------

describe("detectCriticalMoments", () => {
  it("returns empty set for empty array", () => {
    expect(detectCriticalMoments([])).toEqual(new Set());
  });

  it("returns empty set for single data point", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 50, isCritical: false },
    ];
    expect(detectCriticalMoments(points)).toEqual(new Set());
  });

  it("detects change > 100cp as critical", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 0, isCritical: false },
      { moveIndex: 1, clampedEval: 200, isCritical: false },
    ];
    const result = detectCriticalMoments(points);
    expect(result.has(1)).toBe(true);
  });

  it("does NOT mark change of exactly 100cp as critical", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 0, isCritical: false },
      { moveIndex: 1, clampedEval: CRITICAL_THRESHOLD, isCritical: false },
    ];
    const result = detectCriticalMoments(points);
    expect(result.has(1)).toBe(false);
  });

  it("detects negative swing as critical", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 500, isCritical: false },
      { moveIndex: 1, clampedEval: 300, isCritical: false },
    ];
    const result = detectCriticalMoments(points);
    expect(result.has(1)).toBe(true);
  });

  it("detects multiple critical moments", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 0, isCritical: false },
      { moveIndex: 1, clampedEval: 50, isCritical: false },
      { moveIndex: 2, clampedEval: 300, isCritical: false },
      { moveIndex: 3, clampedEval: 310, isCritical: false },
      { moveIndex: 4, clampedEval: -100, isCritical: false },
    ];
    const result = detectCriticalMoments(points);
    expect(result.has(0)).toBe(false); // first, no predecessor
    expect(result.has(1)).toBe(false); // |50 - 0| = 50 ≤ 100
    expect(result.has(2)).toBe(true);  // |300 - 50| = 250 > 100
    expect(result.has(3)).toBe(false); // |310 - 300| = 10 ≤ 100
    expect(result.has(4)).toBe(true);  // |-100 - 310| = 410 > 100
  });

  it("the first position is never critical", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 1500, isCritical: false },
      { moveIndex: 1, clampedEval: 1500, isCritical: false },
    ];
    const result = detectCriticalMoments(points);
    expect(result.has(0)).toBe(false);
  });
});

// -----------------------------------------------------------------------
// prepareGraphData
// -----------------------------------------------------------------------

describe("prepareGraphData", () => {
  it("returns empty array for empty input", () => {
    expect(prepareGraphData([])).toEqual([]);
  });

  it("omits positions with null evaluation and null mateIn", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 50, mateIn: null },
      { moveIndex: 1, evaluation: null, mateIn: null },
      { moveIndex: 2, evaluation: 100, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result).toHaveLength(2);
    expect(result[0].moveIndex).toBe(0);
    expect(result[1].moveIndex).toBe(2);
  });

  it("preserves moveIndex mapping on X-axis after filtering", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 10, mateIn: null },
      { moveIndex: 1, evaluation: null, mateIn: null },
      { moveIndex: 2, evaluation: null, mateIn: null },
      { moveIndex: 3, evaluation: 20, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result.map((p) => p.moveIndex)).toEqual([0, 3]);
  });

  it("clamps evaluations in the output", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 5000, mateIn: null },
      { moveIndex: 1, evaluation: -3000, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result[0].clampedEval).toBe(MAX_EVAL);
    expect(result[1].clampedEval).toBe(-MAX_EVAL);
  });

  it("represents mate-in-N at ±2000 boundary", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: null, mateIn: 3 },
      { moveIndex: 1, evaluation: null, mateIn: -2 },
    ];
    const result = prepareGraphData(input);
    expect(result[0].clampedEval).toBe(MAX_EVAL);
    expect(result[1].clampedEval).toBe(-MAX_EVAL);
  });

  it("marks critical moments in the output", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 0, mateIn: null },
      { moveIndex: 1, evaluation: 50, mateIn: null },
      { moveIndex: 2, evaluation: 300, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result[0].isCritical).toBe(false);
    expect(result[1].isCritical).toBe(false); // |50 - 0| = 50
    expect(result[2].isCritical).toBe(true);  // |300 - 50| = 250
  });

  it("returns all positions when none are null", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 10, mateIn: null },
      { moveIndex: 1, evaluation: 20, mateIn: null },
      { moveIndex: 2, evaluation: 30, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result).toHaveLength(3);
  });

  it("returns empty array when all positions are null", () => {
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: null, mateIn: null },
      { moveIndex: 1, evaluation: null, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result).toHaveLength(0);
  });

  it("detects critical moment across a gap correctly", () => {
    // After filtering, moveIndex 0 and 2 are adjacent in the graph data
    const input: EvalDataPoint[] = [
      { moveIndex: 0, evaluation: 0, mateIn: null },
      { moveIndex: 1, evaluation: null, mateIn: null },
      { moveIndex: 2, evaluation: 500, mateIn: null },
    ];
    const result = prepareGraphData(input);
    expect(result).toHaveLength(2);
    // |500 - 0| = 500 > 100 → critical
    expect(result[1].isCritical).toBe(true);
  });
});

// -----------------------------------------------------------------------
// findNearestMoveIndex
// -----------------------------------------------------------------------

describe("findNearestMoveIndex", () => {
  it("returns -1 for empty data", () => {
    expect(findNearestMoveIndex([], 5)).toBe(-1);
  });

  it("returns the only moveIndex for a single point", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 3, clampedEval: 100, isCritical: false },
    ];
    expect(findNearestMoveIndex(points, 0)).toBe(3);
    expect(findNearestMoveIndex(points, 10)).toBe(3);
  });

  it("returns the nearest moveIndex", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 0, isCritical: false },
      { moveIndex: 5, clampedEval: 100, isCritical: false },
      { moveIndex: 10, clampedEval: 200, isCritical: false },
    ];
    expect(findNearestMoveIndex(points, 3)).toBe(5);
    expect(findNearestMoveIndex(points, 8)).toBe(10);
    expect(findNearestMoveIndex(points, 0)).toBe(0);
  });

  it("returns exact match when target is a data point", () => {
    const points: GraphDataPoint[] = [
      { moveIndex: 0, clampedEval: 0, isCritical: false },
      { moveIndex: 5, clampedEval: 100, isCritical: false },
    ];
    expect(findNearestMoveIndex(points, 5)).toBe(5);
  });
});
