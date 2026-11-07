import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ChessBoard from "./ChessBoard";

// Mock react-chessboard since it relies on DOM features unavailable in jsdom
vi.mock("react-chessboard", () => ({
  Chessboard: ({ options }: { options: Record<string, unknown> }) => (
    <div
      data-testid="mock-chessboard"
      data-position={options.position as string}
      data-square-styles={JSON.stringify(options.squareStyles)}
      data-arrows={JSON.stringify(options.arrows)}
      data-allow-dragging={String(options.allowDragging)}
    />
  ),
}));

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

describe("ChessBoard component", () => {
  it("renders the board container and evaluation bar", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
      />,
    );

    expect(screen.getByTestId("chess-board-container")).toBeInTheDocument();
    expect(screen.getByTestId("chess-board")).toBeInTheDocument();
    expect(screen.getByTestId("evaluation-bar")).toBeInTheDocument();
  });

  it("passes the FEN position to react-chessboard", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    expect(board).toHaveAttribute("data-position", STARTING_FEN);
  });

  it("disables dragging on the board (review-only mode)", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    expect(board).toHaveAttribute("data-allow-dragging", "false");
  });

  it("passes evaluation to EvaluationBar", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={250}
        mateIn={null}
      />,
    );

    // EvaluationBar should render the formatted label
    expect(screen.getByText("+2.5")).toBeInTheDocument();
  });

  it("passes mate info to EvaluationBar", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={null}
        mateIn={3}
      />,
    );

    expect(screen.getByText("M3")).toBeInTheDocument();
  });

  it("highlights best move squares when bestMove is provided", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={{ from: "e2", to: "e4" }}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    const styles = JSON.parse(
      board.getAttribute("data-square-styles") ?? "{}",
    );

    // Both origin and destination squares should have highlight styles
    expect(styles).toHaveProperty("e2");
    expect(styles).toHaveProperty("e4");
    expect(styles.e2.backgroundColor).toBeDefined();
    expect(styles.e4.backgroundColor).toBeDefined();
  });

  it("does not highlight squares when bestMove is null", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    const styles = JSON.parse(
      board.getAttribute("data-square-styles") ?? "{}",
    );

    expect(Object.keys(styles)).toHaveLength(0);
  });

  it("shows a best-move arrow when bestMove is provided", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={{ from: "d2", to: "d4" }}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    const arrows = JSON.parse(
      board.getAttribute("data-arrows") ?? "[]",
    );

    expect(arrows).toHaveLength(1);
    expect(arrows[0].startSquare).toBe("d2");
    expect(arrows[0].endSquare).toBe("d4");
    expect(arrows[0].color).toBeDefined();
  });

  it("shows no arrows when bestMove is null", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    const arrows = JSON.parse(
      board.getAttribute("data-arrows") ?? "[]",
    );

    expect(arrows).toHaveLength(0);
  });

  it("applies custom board width", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={null}
        evaluation={0}
        mateIn={null}
        boardWidth={400}
      />,
    );

    const wrapper = screen.getByTestId("chess-board");
    expect(wrapper.style.width).toBe("400px");
    expect(wrapper.style.height).toBe("400px");
  });

  it("uses the best-move highlight color distinct from default", () => {
    render(
      <ChessBoard
        fen={STARTING_FEN}
        bestMove={{ from: "g1", to: "f3" }}
        evaluation={0}
        mateIn={null}
      />,
    );

    const board = screen.getByTestId("mock-chessboard");
    const styles = JSON.parse(
      board.getAttribute("data-square-styles") ?? "{}",
    );

    // The highlight should use a blue-ish color (distinct from player-move yellow/green)
    const highlightColor = styles.g1.backgroundColor;
    expect(highlightColor).toContain("rgba");
    // Both squares should have the same highlight style
    expect(styles.g1.backgroundColor).toBe(styles.f3.backgroundColor);
  });
});
