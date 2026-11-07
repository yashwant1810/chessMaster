import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { GameSummary } from "../types";
import GameList from "./GameList";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderGameList(games: GameSummary[]) {
  return render(
    <MemoryRouter>
      <GameList games={games} />
    </MemoryRouter>,
  );
}

function makeGame(overrides: Partial<GameSummary> & { game_id: string }): GameSummary {
  return {
    date_played: "2024-06-15T12:00:00Z",
    opponent: "opponent1",
    result: "win",
    time_control: "600",
    opening_name: "Sicilian Defense",
    is_analyzed: false,
    ...overrides,
  };
}

const SAMPLE_GAMES: GameSummary[] = [
  makeGame({
    game_id: "g1",
    date_played: "2024-01-10T10:00:00Z",
    opponent: "alice",
    result: "win",
    time_control: "300",
    opening_name: "Italian Game",
  }),
  makeGame({
    game_id: "g2",
    date_played: "2024-03-20T14:00:00Z",
    opponent: "bob",
    result: "loss",
    time_control: "600",
    opening_name: "French Defense",
  }),
  makeGame({
    game_id: "g3",
    date_played: "2024-02-05T08:00:00Z",
    opponent: "carol",
    result: "draw",
    time_control: "900",
    opening_name: null,
  }),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockNavigate.mockClear();
});

describe("GameList", () => {
  it("renders empty state when there are no games", () => {
    renderGameList([]);
    expect(screen.getByTestId("game-list-empty")).toBeInTheDocument();
    expect(screen.getByText("No games available.")).toBeInTheDocument();
  });

  it("renders game items when games are provided", () => {
    renderGameList(SAMPLE_GAMES);
    expect(screen.getByTestId("game-list")).toBeInTheDocument();
    expect(screen.getByTestId("game-item-g1")).toBeInTheDocument();
    expect(screen.getByTestId("game-item-g2")).toBeInTheDocument();
    expect(screen.getByTestId("game-item-g3")).toBeInTheDocument();
  });

  it("sorts by date descending (most recent first) by default", () => {
    renderGameList(SAMPLE_GAMES);
    const rows = screen.getAllByRole("row").slice(1); // skip header
    // g2 (March) > g3 (Feb) > g1 (Jan) — desc
    expect(within(rows[0]).getByText("bob")).toBeInTheDocument();
    expect(within(rows[1]).getByText("carol")).toBeInTheDocument();
    expect(within(rows[2]).getByText("alice")).toBeInTheDocument();
  });

  it("toggles date sort to ascending on click", async () => {
    const user = userEvent.setup();
    renderGameList(SAMPLE_GAMES);

    const dateBtn = screen.getByRole("button", { name: /sort by date/i });
    await user.click(dateBtn); // toggle to asc

    const rows = screen.getAllByRole("row").slice(1);
    // g1 (Jan) < g3 (Feb) < g2 (March) — asc
    expect(within(rows[0]).getByText("alice")).toBeInTheDocument();
    expect(within(rows[1]).getByText("carol")).toBeInTheDocument();
    expect(within(rows[2]).getByText("bob")).toBeInTheDocument();
  });

  it("sorts by result when result button is clicked", async () => {
    const user = userEvent.setup();
    renderGameList(SAMPLE_GAMES);

    await user.click(screen.getByRole("button", { name: /sort by result/i }));

    const rows = screen.getAllByRole("row").slice(1);
    // asc: win < draw < loss
    expect(within(rows[0]).getByText("Win")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Draw")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Loss")).toBeInTheDocument();
  });

  it("sorts by time control when time control button is clicked", async () => {
    const user = userEvent.setup();
    renderGameList(SAMPLE_GAMES);

    await user.click(
      screen.getByRole("button", { name: /sort by time control/i }),
    );

    const rows = screen.getAllByRole("row").slice(1);
    // asc string order: "300" < "600" < "900"
    expect(within(rows[0]).getByText("300")).toBeInTheDocument();
    expect(within(rows[1]).getByText("600")).toBeInTheDocument();
    expect(within(rows[2]).getByText("900")).toBeInTheDocument();
  });

  it("navigates to analysis view on game row click", async () => {
    const user = userEvent.setup();
    renderGameList(SAMPLE_GAMES);

    await user.click(screen.getByTestId("game-item-g1"));
    expect(mockNavigate).toHaveBeenCalledWith("/analysis/g1");
  });

  it("navigates on Enter key press", async () => {
    const user = userEvent.setup();
    renderGameList(SAMPLE_GAMES);

    const row = screen.getByTestId("game-item-g2");
    row.focus();
    await user.keyboard("{Enter}");
    expect(mockNavigate).toHaveBeenCalledWith("/analysis/g2");
  });

  it("displays sort direction indicators", () => {
    renderGameList(SAMPLE_GAMES);
    // Date is active by default with desc order
    expect(screen.getByText("↓")).toBeInTheDocument();
  });

  it("renders table headers", () => {
    renderGameList(SAMPLE_GAMES);
    const headers = screen.getAllByRole("columnheader");
    const headerTexts = headers.map((h) => h.textContent);
    expect(headerTexts).toEqual(["Date", "Opponent", "Result", "Time Control", "Opening"]);
  });
});
