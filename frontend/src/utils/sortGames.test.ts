import type { GameSummary } from "../types";
import { sortGames } from "./sortGames";

function makeGame(overrides: Partial<GameSummary> & { game_id: string }): GameSummary {
  return {
    date_played: "2024-06-15T12:00:00Z",
    opponent: "opponent",
    result: "win",
    time_control: "600",
    opening_name: "Sicilian",
    is_analyzed: false,
    ...overrides,
  };
}

describe("sortGames", () => {
  const games: GameSummary[] = [
    makeGame({ game_id: "g1", date_played: "2024-01-10T10:00:00Z", result: "win", time_control: "300" }),
    makeGame({ game_id: "g2", date_played: "2024-03-20T14:00:00Z", result: "loss", time_control: "600" }),
    makeGame({ game_id: "g3", date_played: "2024-02-05T08:00:00Z", result: "draw", time_control: "900" }),
  ];

  it("sorts by date descending (most recent first)", () => {
    const result = sortGames(games, "date", "desc");
    expect(result.map((g) => g.game_id)).toEqual(["g2", "g3", "g1"]);
  });

  it("sorts by date ascending (oldest first)", () => {
    const result = sortGames(games, "date", "asc");
    expect(result.map((g) => g.game_id)).toEqual(["g1", "g3", "g2"]);
  });

  it("sorts by result ascending (win, draw, loss)", () => {
    const result = sortGames(games, "result", "asc");
    expect(result.map((g) => g.result)).toEqual(["win", "draw", "loss"]);
  });

  it("sorts by result descending (loss, draw, win)", () => {
    const result = sortGames(games, "result", "desc");
    expect(result.map((g) => g.result)).toEqual(["loss", "draw", "win"]);
  });

  it("sorts by time_control ascending", () => {
    const result = sortGames(games, "time_control", "asc");
    expect(result.map((g) => g.time_control)).toEqual(["300", "600", "900"]);
  });

  it("sorts by time_control descending", () => {
    const result = sortGames(games, "time_control", "desc");
    expect(result.map((g) => g.time_control)).toEqual(["900", "600", "300"]);
  });

  it("does not mutate the input array", () => {
    const copy = [...games];
    sortGames(games, "date", "asc");
    expect(games).toEqual(copy);
  });

  it("returns an empty array for empty input", () => {
    expect(sortGames([], "date", "desc")).toEqual([]);
  });

  it("places null time_control last regardless of sort order", () => {
    const withNull = [
      makeGame({ game_id: "a", time_control: null }),
      makeGame({ game_id: "b", time_control: "300" }),
      makeGame({ game_id: "c", time_control: "600" }),
    ];

    const asc = sortGames(withNull, "time_control", "asc");
    expect(asc[asc.length - 1].game_id).toBe("a");

    const desc = sortGames(withNull, "time_control", "desc");
    expect(desc[desc.length - 1].game_id).toBe("a");
  });

  it("preserves all games (same length, same elements)", () => {
    const result = sortGames(games, "date", "desc");
    expect(result).toHaveLength(games.length);
    const ids = result.map((g) => g.game_id).sort();
    const originalIds = games.map((g) => g.game_id).sort();
    expect(ids).toEqual(originalIds);
  });
});
