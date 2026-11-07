/**
 * Property 7: Game List Sort Correctness
 *
 * **Validates: Requirements 3.1, 3.4**
 *
 * For any list of game summaries and any valid sort configuration
 * (sort field: date, result, time_control; sort order: asc, desc),
 * the sorted output SHALL:
 *   1. Contain exactly the same games as the input (permutation).
 *   2. Have each consecutive pair satisfying the specified ordering.
 */
import * as fc from "fast-check";
import { describe, it, expect } from "vitest";
import { sortGames } from "../utils/sortGames";
import type { GameSummary, SortField, SortOrder } from "../types";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

const resultArb = fc.constantFrom("win", "loss", "draw") as fc.Arbitrary<
  "win" | "loss" | "draw"
>;

/** Generates a plausible ISO 8601 date-time string via integer timestamps. */
const MIN_TS = new Date("2000-01-01T00:00:00Z").getTime();
const MAX_TS = new Date("2030-12-31T23:59:59Z").getTime();
const dateArb = fc
  .integer({ min: MIN_TS, max: MAX_TS })
  .map((ts) => new Date(ts).toISOString());

/** Generates a nullable time-control string (e.g. "600", "180+2", null). */
const timeControlArb: fc.Arbitrary<string | null> = fc.oneof(
  fc.constant(null),
  fc
    .array(fc.constantFrom("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "+", "/"), {
      minLength: 1,
      maxLength: 10,
    })
    .map((chars) => chars.join("")),
);

/** Generates a single GameSummary with random data. */
const gameSummaryArb: fc.Arbitrary<GameSummary> = fc
  .tuple(fc.uuid(), dateArb, fc.string({ minLength: 1, maxLength: 20 }), resultArb, timeControlArb, fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }), fc.boolean())
  .map(([id, date, opponent, result, tc, opening, analyzed]) => ({
    game_id: id,
    date_played: date,
    opponent,
    result,
    time_control: tc,
    opening_name: opening,
    is_analyzed: analyzed,
  }));

const gameSummaryArrayArb = fc.array(gameSummaryArb, { minLength: 0, maxLength: 50 });

const sortFieldArb: fc.Arbitrary<SortField> = fc.constantFrom(
  "date",
  "result",
  "time_control",
);

const sortOrderArb: fc.Arbitrary<SortOrder> = fc.constantFrom("asc", "desc");

// ---------------------------------------------------------------------------
// Comparison helpers — mirror the production sort logic for verification
// ---------------------------------------------------------------------------

const RESULT_ORDER: Record<string, number> = { win: 0, draw: 1, loss: 2 };

function compareByField(
  a: GameSummary,
  b: GameSummary,
  field: SortField,
): number {
  switch (field) {
    case "date":
      return a.date_played.localeCompare(b.date_played);
    case "result":
      return (RESULT_ORDER[a.result] ?? 3) - (RESULT_ORDER[b.result] ?? 3);
    case "time_control": {
      if (a.time_control === null && b.time_control === null) return 0;
      if (a.time_control === null) return 1;
      if (b.time_control === null) return -1;
      return a.time_control.localeCompare(b.time_control);
    }
    default:
      return 0;
  }
}

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

describe("Property 7: Game List Sort Correctness", () => {
  it("sorted output is a permutation of the input", () => {
    fc.assert(
      fc.property(
        gameSummaryArrayArb,
        sortFieldArb,
        sortOrderArb,
        (games, field, order) => {
          const sorted = sortGames(games, field, order);

          // Same length
          expect(sorted).toHaveLength(games.length);

          // Same set of game_ids (including duplicates if any)
          const inputIds = games.map((g) => g.game_id).sort();
          const outputIds = sorted.map((g) => g.game_id).sort();
          expect(outputIds).toEqual(inputIds);
        },
      ),
      { numRuns: 200 },
    );
  });

  it("consecutive pairs satisfy the specified ordering", () => {
    fc.assert(
      fc.property(
        gameSummaryArrayArb,
        sortFieldArb,
        sortOrderArb,
        (games, field, order) => {
          const sorted = sortGames(games, field, order);
          const direction = order === "asc" ? 1 : -1;

          for (let i = 0; i < sorted.length - 1; i++) {
            const cmp = compareByField(sorted[i], sorted[i + 1], field);

            if (field === "time_control") {
              // Nulls sort last regardless of direction — special case in impl
              const aNull = sorted[i].time_control === null;
              const bNull = sorted[i + 1].time_control === null;

              if (aNull && bNull) {
                // Both null — order between them is stable but comparison is 0
                continue;
              }
              if (!aNull && bNull) {
                // Non-null before null is always valid (null sorts last)
                continue;
              }
              if (aNull && !bNull) {
                // Null before non-null should never happen
                expect.unreachable(
                  `null time_control appeared before non-null at index ${i}`,
                );
              }
              // Both non-null: cmp <= 0 for asc, cmp >= 0 for desc
              expect(cmp * direction).toBeLessThanOrEqual(0);
            } else {
              // For date & result: sorted[i] should precede sorted[i+1]
              // so cmp <= 0 for asc (direction 1), cmp >= 0 for desc (direction -1)
              expect(cmp * direction).toBeLessThanOrEqual(0);
            }
          }
        },
      ),
      { numRuns: 200 },
    );
  });

  it("does not mutate the original array", () => {
    fc.assert(
      fc.property(
        gameSummaryArrayArb,
        sortFieldArb,
        sortOrderArb,
        (games, field, order) => {
          const snapshot = games.map((g) => g.game_id);
          sortGames(games, field, order);
          const afterIds = games.map((g) => g.game_id);
          expect(afterIds).toEqual(snapshot);
        },
      ),
      { numRuns: 100 },
    );
  });
});
