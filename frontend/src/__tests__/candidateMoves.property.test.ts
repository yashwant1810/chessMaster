/**
 * Property 9: Candidate Moves Display Correctness
 *
 * **Validates: Requirements 7.1, 7.3, 7.4**
 *
 * For any position with N legal moves where N ≥ 1, the candidate moves
 * display SHALL show min(N, 3) candidate moves sorted in descending order
 * of centipawn evaluation, SHALL display the centipawn evaluation for each
 * candidate and for the player's actual move, and SHALL visually mark the
 * player's move within the candidate list if the player's move is among
 * the displayed candidates.
 */
import * as fc from "fast-check";
import { describe, it, expect } from "vitest";
import type { CandidateMove } from "../types";
import {
  sortCandidatesByEval,
  effectiveScore,
  limitCandidates,
  formatEvaluation,
  prepareDisplayCandidates,
} from "../utils/candidateMoves";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/** Generates a SAN-like move string (e.g. "e4", "Nf3", "Qxd7+"). */
const moveSanArb: fc.Arbitrary<string> = fc.oneof(
  // Pawn moves: e4, d5, a3
  fc
    .tuple(
      fc.constantFrom("a", "b", "c", "d", "e", "f", "g", "h"),
      fc.constantFrom("1", "2", "3", "4", "5", "6", "7", "8"),
    )
    .map(([file, rank]) => `${file}${rank}`),
  // Piece moves: Nf3, Bb5, Qd1
  fc
    .tuple(
      fc.constantFrom("N", "B", "R", "Q", "K"),
      fc.constantFrom("a", "b", "c", "d", "e", "f", "g", "h"),
      fc.constantFrom("1", "2", "3", "4", "5", "6", "7", "8"),
    )
    .map(([piece, file, rank]) => `${piece}${file}${rank}`),
  // Captures: exd5, Nxf6
  fc
    .tuple(
      fc.constantFrom("e", "N", "B", "R", "Q"),
      fc.constant("x"),
      fc.constantFrom("a", "b", "c", "d", "e", "f", "g", "h"),
      fc.constantFrom("1", "2", "3", "4", "5", "6", "7", "8"),
    )
    .map(([src, x, file, rank]) => `${src}${x}${file}${rank}`),
);

/** Generates a unique array of SAN move strings (no duplicates). */
const uniqueMoveSanArrayArb = (minLen: number, maxLen: number) =>
  fc.uniqueArray(moveSanArb, {
    minLength: minLen,
    maxLength: maxLen,
    comparator: (a, b) => a === b,
  });

/** Generates a centipawn evaluation: a number in [-3000, +3000] or null. */
const evalArb: fc.Arbitrary<number | null> = fc.oneof(
  fc.integer({ min: -3000, max: 3000 }),
  fc.constant(null),
);

/** Generates a mate_in value: small signed integer or null. */
const mateInArb: fc.Arbitrary<number | null> = fc.oneof(
  fc.integer({ min: -20, max: -1 }),
  fc.integer({ min: 1, max: 20 }),
  fc.constant(null),
);

/** Generates a single CandidateMove with a given SAN to ensure uniqueness. */
const candidateMoveFromSan = (san: string): fc.Arbitrary<CandidateMove> =>
  fc.tuple(evalArb, mateInArb).map(([evaluation, mate_in]) => ({
    move_san: san,
    evaluation,
    mate_in,
  }));

/**
 * Generates an array of 1–8 CandidateMove objects with unique SANs.
 * This mirrors positions with varying numbers of legal moves.
 */
const candidateMovesArb: fc.Arbitrary<CandidateMove[]> = uniqueMoveSanArrayArb(
  1,
  8,
).chain((sans) =>
  fc.tuple(...sans.map((san) => candidateMoveFromSan(san))).map((moves) => [
    ...moves,
  ]),
);

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

describe("Property 9: Candidate Moves Display Correctness", () => {
  it("displays min(N, 3) candidates from any input array", () => {
    fc.assert(
      fc.property(candidateMovesArb, (candidates) => {
        const limited = limitCandidates(sortCandidatesByEval(candidates), 3);
        expect(limited).toHaveLength(Math.min(candidates.length, 3));
      }),
      { numRuns: 200 },
    );
  });

  it("candidates are sorted in descending evaluation order", () => {
    fc.assert(
      fc.property(candidateMovesArb, (candidates) => {
        const sorted = sortCandidatesByEval(candidates);

        for (let i = 0; i < sorted.length - 1; i++) {
          const scoreA = effectiveScore(sorted[i]);
          const scoreB = effectiveScore(sorted[i + 1]);
          expect(scoreA).toBeGreaterThanOrEqual(scoreB);
        }
      }),
      { numRuns: 200 },
    );
  });

  it("each displayed candidate has a formatted evaluation string", () => {
    fc.assert(
      fc.property(candidateMovesArb, (candidates) => {
        const sorted = sortCandidatesByEval(candidates);
        const limited = limitCandidates(sorted, 3);

        for (const c of limited) {
          const formatted = formatEvaluation(c.evaluation, c.mate_in);
          expect(typeof formatted).toBe("string");
          expect(formatted.length).toBeGreaterThan(0);

          // Verify format correctness
          if (c.mate_in !== null) {
            // Mate-in format: "M+N" or "M-N"
            expect(formatted).toMatch(/^M[+-]\d+$/);
          } else if (c.evaluation !== null) {
            // Centipawn format: "+N", "-N", or "0"
            if (c.evaluation > 0) {
              expect(formatted).toMatch(/^\+\d+$/);
            } else if (c.evaluation < 0) {
              expect(formatted).toMatch(/^-\d+$/);
            } else {
              expect(formatted).toBe("0");
            }
          } else {
            // Null evaluation shows en-dash
            expect(formatted).toBe("–");
          }
        }
      }),
      { numRuns: 200 },
    );
  });

  it("marks player's move if present in candidates", () => {
    fc.assert(
      fc.property(
        candidateMovesArb,
        fc.boolean(),
        (candidates, usePlayerFromList) => {
          // Pick a player move: either from the candidate list or a fresh one
          const playerMove = usePlayerFromList
            ? candidates[
                Math.floor(Math.random() * candidates.length)
              ].move_san
            : "O-O"; // castling — unlikely to appear in random SAN generation

          const display = prepareDisplayCandidates(candidates, playerMove);

          // Check the min(N,3) length invariant
          expect(display).toHaveLength(Math.min(candidates.length, 3));

          // If player's move is in the original list AND made it into top 3,
          // it should be marked
          const isInDisplay = display.some((d) => d.move_san === playerMove);

          if (isInDisplay) {
            const playerEntry = display.find(
              (d) => d.move_san === playerMove,
            )!;
            expect(playerEntry.isPlayerMove).toBe(true);
          }

          // All non-player entries must NOT be marked
          for (const d of display) {
            if (d.move_san !== playerMove) {
              expect(d.isPlayerMove).toBe(false);
            }
          }

          // Each entry has a formatted eval
          for (const d of display) {
            expect(typeof d.formattedEval).toBe("string");
            expect(d.formattedEval.length).toBeGreaterThan(0);
          }
        },
      ),
      { numRuns: 200 },
    );
  });

  it("prepareDisplayCandidates output is sorted descending by evaluation", () => {
    fc.assert(
      fc.property(candidateMovesArb, moveSanArb, (candidates, playerMove) => {
        const display = prepareDisplayCandidates(candidates, playerMove);

        // Map display back to the original candidates to get their effective scores
        const originalMap = new Map(
          candidates.map((c) => [c.move_san, c]),
        );

        for (let i = 0; i < display.length - 1; i++) {
          const currOriginal = originalMap.get(display[i].move_san);
          const nextOriginal = originalMap.get(display[i + 1].move_san);

          if (currOriginal && nextOriginal) {
            expect(effectiveScore(currOriginal)).toBeGreaterThanOrEqual(
              effectiveScore(nextOriginal),
            );
          }
        }
      }),
      { numRuns: 200 },
    );
  });

  it("does not mutate the input candidate array", () => {
    fc.assert(
      fc.property(candidateMovesArb, moveSanArb, (candidates, playerMove) => {
        const snapshot = candidates.map((c) => ({ ...c }));

        prepareDisplayCandidates(candidates, playerMove);

        // Original array should be unchanged
        expect(candidates).toHaveLength(snapshot.length);
        for (let i = 0; i < candidates.length; i++) {
          expect(candidates[i].move_san).toBe(snapshot[i].move_san);
          expect(candidates[i].evaluation).toBe(snapshot[i].evaluation);
          expect(candidates[i].mate_in).toBe(snapshot[i].mate_in);
        }
      }),
      { numRuns: 100 },
    );
  });
});
