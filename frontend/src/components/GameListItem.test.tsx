import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { GameSummary } from "../types";
import GameListItem from "./GameListItem";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderItem(game: GameSummary, onSelect = vi.fn()) {
  return {
    onSelect,
    ...render(
      <table>
        <tbody>
          <GameListItem game={game} onSelect={onSelect} />
        </tbody>
      </table>,
    ),
  };
}

function makeGame(overrides: Partial<GameSummary> = {}): GameSummary {
  return {
    game_id: "test-id",
    date_played: "2024-06-15T12:00:00Z",
    opponent: "opponent1",
    result: "win",
    time_control: "600",
    opening_name: "Sicilian Defense",
    is_analyzed: false,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("GameListItem", () => {
  it("renders all metadata fields when present", () => {
    renderItem(makeGame());
    expect(screen.getByText("opponent1")).toBeInTheDocument();
    expect(screen.getByText("Win")).toBeInTheDocument();
    expect(screen.getByText("600")).toBeInTheDocument();
    expect(screen.getByText("Sicilian Defense")).toBeInTheDocument();
  });

  it("displays 'unavailable' for null time_control", () => {
    renderItem(makeGame({ time_control: null }));
    const unavailables = screen.getAllByText("unavailable");
    expect(unavailables.length).toBeGreaterThanOrEqual(1);
  });

  it("displays 'unavailable' for null opening_name", () => {
    renderItem(makeGame({ opening_name: null }));
    const unavailables = screen.getAllByText("unavailable");
    expect(unavailables.length).toBeGreaterThanOrEqual(1);
  });

  it("displays 'unavailable' for both null time_control and opening_name", () => {
    renderItem(makeGame({ time_control: null, opening_name: null }));
    const unavailables = screen.getAllByText("unavailable");
    expect(unavailables).toHaveLength(2);
  });

  it("renders loss result", () => {
    renderItem(makeGame({ result: "loss" }));
    expect(screen.getByText("Loss")).toBeInTheDocument();
  });

  it("renders draw result", () => {
    renderItem(makeGame({ result: "draw" }));
    expect(screen.getByText("Draw")).toBeInTheDocument();
  });

  it("calls onSelect with game_id on click", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderItem(makeGame({ game_id: "abc-123" }));

    await user.click(screen.getByTestId("game-item-abc-123"));
    expect(onSelect).toHaveBeenCalledWith("abc-123");
  });

  it("calls onSelect on Enter key press", async () => {
    const user = userEvent.setup();
    const { onSelect } = renderItem(makeGame({ game_id: "key-test" }));

    const row = screen.getByTestId("game-item-key-test");
    row.focus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("key-test");
  });

  it("formats the date for display", () => {
    renderItem(makeGame({ date_played: "2024-12-25T00:00:00Z" }));
    // Date formatting varies by locale, but should contain "2024" and "25"
    const row = screen.getByTestId("game-item-test-id");
    expect(row.textContent).toContain("2024");
    expect(row.textContent).toContain("25");
  });
});
