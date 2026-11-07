import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import GameSummary from "./GameSummary";
import type { PlayerAnalysisSummary } from "../types";

function makeSummary(overrides: Partial<PlayerAnalysisSummary> = {}): PlayerAnalysisSummary {
  return {
    best_count: 5,
    excellent_count: 3,
    good_count: 4,
    inaccuracy_count: 2,
    mistake_count: 1,
    blunder_count: 0,
    performance_ratings: [1500, 1520, 1510],
    final_performance_rating: 1510,
    ...overrides,
  };
}

describe("GameSummary", () => {
  it("renders unavailable message when both summaries are null", () => {
    render(
      <GameSummary
        whiteSummary={null}
        blackSummary={null}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("game-summary-unavailable")).toHaveTextContent(
      "Performance data requires completed analysis",
    );
    expect(screen.queryByTestId("player-summary-Alice")).not.toBeInTheDocument();
    expect(screen.queryByTestId("player-summary-Bob")).not.toBeInTheDocument();
  });

  it("renders unavailable message when white summary is null", () => {
    render(
      <GameSummary
        whiteSummary={null}
        blackSummary={makeSummary()}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("game-summary-unavailable")).toBeInTheDocument();
  });

  it("renders unavailable message when black summary is null", () => {
    render(
      <GameSummary
        whiteSummary={makeSummary()}
        blackSummary={null}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("game-summary-unavailable")).toBeInTheDocument();
  });

  it("renders player names when summaries are provided", () => {
    render(
      <GameSummary
        whiteSummary={makeSummary()}
        blackSummary={makeSummary()}
        whitePlayer="Magnus"
        blackPlayer="Hikaru"
      />,
    );

    expect(screen.getByTestId("player-summary-Magnus")).toBeInTheDocument();
    expect(screen.getByTestId("player-summary-Hikaru")).toBeInTheDocument();
  });

  it("displays correct classification counts for white player", () => {
    const whiteSummary = makeSummary({
      best_count: 10,
      excellent_count: 7,
      good_count: 5,
      inaccuracy_count: 3,
      mistake_count: 2,
      blunder_count: 1,
    });

    render(
      <GameSummary
        whiteSummary={whiteSummary}
        blackSummary={makeSummary()}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("Alice-best-count")).toHaveTextContent("10");
    expect(screen.getByTestId("Alice-excellent-count")).toHaveTextContent("7");
    expect(screen.getByTestId("Alice-good-count")).toHaveTextContent("5");
    expect(screen.getByTestId("Alice-inaccuracy-count")).toHaveTextContent("3");
    expect(screen.getByTestId("Alice-mistake-count")).toHaveTextContent("2");
    expect(screen.getByTestId("Alice-blunder-count")).toHaveTextContent("1");
  });

  it("displays correct classification counts for black player", () => {
    const blackSummary = makeSummary({
      best_count: 8,
      excellent_count: 6,
      good_count: 4,
      inaccuracy_count: 1,
      mistake_count: 0,
      blunder_count: 3,
    });

    render(
      <GameSummary
        whiteSummary={makeSummary()}
        blackSummary={blackSummary}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("Bob-best-count")).toHaveTextContent("8");
    expect(screen.getByTestId("Bob-excellent-count")).toHaveTextContent("6");
    expect(screen.getByTestId("Bob-good-count")).toHaveTextContent("4");
    expect(screen.getByTestId("Bob-inaccuracy-count")).toHaveTextContent("1");
    expect(screen.getByTestId("Bob-mistake-count")).toHaveTextContent("0");
    expect(screen.getByTestId("Bob-blunder-count")).toHaveTextContent("3");
  });

  it("displays final performance rating for both players", () => {
    render(
      <GameSummary
        whiteSummary={makeSummary({ final_performance_rating: 2100 })}
        blackSummary={makeSummary({ final_performance_rating: 1850 })}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("Alice-performance-rating")).toHaveTextContent("2100");
    expect(screen.getByTestId("Bob-performance-rating")).toHaveTextContent("1850");
  });

  it("displays all six classification categories with icons", () => {
    render(
      <GameSummary
        whiteSummary={makeSummary()}
        blackSummary={makeSummary()}
        whitePlayer="White"
        blackPlayer="Black"
      />,
    );

    // Each player section has a classifications list
    const lists = screen.getAllByRole("list");
    expect(lists.length).toBe(2);

    // Check all 6 categories are listed for each player (6 items × 2 players = 12)
    const items = screen.getAllByRole("listitem");
    expect(items.length).toBe(12);
  });

  it("renders zero counts correctly", () => {
    const summary = makeSummary({
      best_count: 0,
      excellent_count: 0,
      good_count: 0,
      inaccuracy_count: 0,
      mistake_count: 0,
      blunder_count: 0,
      final_performance_rating: 0,
    });

    render(
      <GameSummary
        whiteSummary={summary}
        blackSummary={summary}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByTestId("Alice-best-count")).toHaveTextContent("0");
    expect(screen.getByTestId("Alice-blunder-count")).toHaveTextContent("0");
    expect(screen.getByTestId("Alice-performance-rating")).toHaveTextContent("0");
  });

  it("renders the Game Summary heading", () => {
    render(
      <GameSummary
        whiteSummary={makeSummary()}
        blackSummary={makeSummary()}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    expect(screen.getByText("Game Summary")).toBeInTheDocument();
  });

  it("does not render player sections when summaries are null", () => {
    render(
      <GameSummary
        whiteSummary={null}
        blackSummary={null}
        whitePlayer="Alice"
        blackPlayer="Bob"
      />,
    );

    // No classification lists should be present
    expect(screen.queryAllByRole("list")).toHaveLength(0);
    // No performance rating elements
    expect(screen.queryByTestId("Alice-performance-rating")).not.toBeInTheDocument();
    expect(screen.queryByTestId("Bob-performance-rating")).not.toBeInTheDocument();
  });
});
