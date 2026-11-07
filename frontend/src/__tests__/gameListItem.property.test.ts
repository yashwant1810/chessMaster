/**
 * Property 8: Game List Item Completeness
 *
 * For any game summary object, the rendered game list item SHALL include the
 * value of every present metadata field (date played, opponent username, game
 * result, time control, opening name) and SHALL display an "unavailable"
 * placeholder for each metadata field that is missing or null.
 *
 * **Validates: Requirements 3.2, 3.6**
 */
import { render, screen } from "@testing-library/react";
import fc from "fast-check";
import { createElement } from "react";
import type { GameSummary, GameResult } from "../types";
import GameListItem from "../components/GameListItem";

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

const RESULTS: GameResult[] = ["win", "loss", "draw"];
const RESULT_LABELS: Record<GameResult, string> = {
  win: "Win",
  loss: "Loss",
  draw: "Draw",
};

/** Generate a non-empty alphanumeric string for IDs and usernames. */
const arbNonEmpty = fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]{0,19}$/);

/** Generate an ISO 8601 date string. */
const arbIsoDate = fc.integer({ min: new Date("2000-01-01").getTime(), max: new Date("2030-12-31").getTime() }).map((ts) => new Date(ts).toISOString());

/** Generate a random GameResult. */
const arbResult = fc.constantFrom<GameResult>(...RESULTS);

/** Generate a random time control string or null. */
const arbTimeControl = fc.oneof(
  fc.constant(null),
  fc.stringMatching(/^[a-zA-Z0-9+/]{1,10}$/),
);

/** Generate a random opening name string or null. */
const arbOpeningName = fc.oneof(
  fc.constant(null),
  fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9 '-]{0,39}$/),
);

/** Generate a full GameSummary with optional null fields. */
const arbGameSummary: fc.Arbitrary<GameSummary> = fc.record({
  game_id: arbNonEmpty,
  date_played: arbIsoDate,
  opponent: arbNonEmpty,
  result: arbResult,
  time_control: arbTimeControl,
  opening_name: arbOpeningName,
  is_analyzed: fc.boolean(),
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderItem(game: GameSummary) {
  const { unmount } = render(
    createElement(
      "table",
      null,
      createElement("tbody", null, createElement(GameListItem, { game, onSelect: () => {} })),
    ),
  );
  return unmount;
}

// ---------------------------------------------------------------------------
// Property test
// ---------------------------------------------------------------------------

describe("Property 8: Game List Item Completeness", () => {
  it("renders all present fields and shows 'unavailable' for null fields", () => {
    fc.assert(
      fc.property(arbGameSummary, (game) => {
        const unmount = renderItem(game);
        const row = screen.getByTestId(`game-item-${game.game_id}`);
        const text = row.textContent ?? "";

        // --- Present fields MUST appear ---
        // Opponent is always present
        expect(text).toContain(game.opponent);

        // Result label is always present
        const label = RESULT_LABELS[game.result];
        expect(text).toContain(label);

        // Time control: present value → rendered; null → "unavailable"
        if (game.time_control !== null) {
          expect(text).toContain(game.time_control);
        }
        if (game.opening_name !== null) {
          expect(text).toContain(game.opening_name);
        }

        // --- Null fields MUST show "unavailable" ---
        const unavailableSpans = row.querySelectorAll(".unavailable");
        const expectedNullCount =
          (game.time_control === null ? 1 : 0) + (game.opening_name === null ? 1 : 0);

        expect(unavailableSpans).toHaveLength(expectedNullCount);

        // Each unavailable span must contain the placeholder text
        unavailableSpans.forEach((span) => {
          expect(span.textContent).toBe("unavailable");
        });

        // Date is always rendered (formatted) — verify it exists as a non-empty cell
        const dateCell = row.querySelector(".game-date");
        expect(dateCell).not.toBeNull();
        expect(dateCell!.textContent!.length).toBeGreaterThan(0);

        unmount();
      }),
      { numRuns: 100 },
    );
  });
});
