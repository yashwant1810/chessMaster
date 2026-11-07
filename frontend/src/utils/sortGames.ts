import type { GameSummary, SortField, SortOrder } from "../types";

/**
 * Pure utility that sorts an array of GameSummary objects.
 *
 * Extracted as a standalone function so it can be property-tested independently
 * (see task 8.6).
 *
 * @returns A **new** sorted array — the input is never mutated.
 */
export function sortGames(
  games: readonly GameSummary[],
  field: SortField,
  order: SortOrder,
): GameSummary[] {
  const sorted = [...games];
  const direction = order === "asc" ? 1 : -1;

  sorted.sort((a, b) => {
    let cmp: number;

    switch (field) {
      case "date":
        cmp = a.date_played.localeCompare(b.date_played);
        break;

      case "result": {
        const resultOrder: Record<string, number> = {
          win: 0,
          draw: 1,
          loss: 2,
        };
        cmp =
          (resultOrder[a.result] ?? 3) - (resultOrder[b.result] ?? 3);
        break;
      }

      case "time_control": {
        // Null values sort last regardless of direction
        if (a.time_control === null && b.time_control === null) return 0;
        if (a.time_control === null) return 1;
        if (b.time_control === null) return -1;
        cmp = a.time_control.localeCompare(b.time_control);
        break;
      }

      default:
        cmp = 0;
    }

    return cmp * direction;
  });

  return sorted;
}
