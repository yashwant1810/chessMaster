import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MoveList from "./MoveList";
import type { AnalyzedMove, MoveClassification } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Minimal PositionEvaluation stub for tests. */
const STUB_EVAL = {
  fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  evaluation: 0,
  mate_in: null,
  candidate_moves: [],
  is_error: false,
};

function makeMove(
  overrides: Partial<AnalyzedMove> & {
    move_number: number;
    is_white: boolean;
    move_san: string;
  },
): AnalyzedMove {
  return {
    position_before: "fen-before",
    position_after: "fen-after",
    evaluation_before: STUB_EVAL,
    evaluation_after: STUB_EVAL,
    classification: "good" as MoveClassification,
    centipawn_loss: 15,
    candidate_moves: [],
    insight: null,
    ...overrides,
  };
}

/**
 * Build a simple game sequence of moves. Each pair of move_number values
 * produces a White move followed by a Black move.
 */
function makeMoves(count: number): AnalyzedMove[] {
  const moves: AnalyzedMove[] = [];
  let moveNum = 1;
  for (let i = 0; i < count; i++) {
    const isWhite = i % 2 === 0;
    if (isWhite) {
      moveNum = Math.floor(i / 2) + 1;
    }
    moves.push(
      makeMove({
        move_number: moveNum,
        is_white: isWhite,
        move_san: `move${i + 1}`,
        classification: "good",
      }),
    );
  }
  return moves;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MoveList", () => {
  it("renders empty state when there are no moves", () => {
    render(<MoveList moves={[]} currentMove={0} onSelect={vi.fn()} />);
    expect(screen.getByTestId("move-list-empty")).toBeInTheDocument();
    expect(screen.getByText("No moves to display.")).toBeInTheDocument();
  });

  it("renders table headers (#, White, Black)", () => {
    const moves = makeMoves(2);
    render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
    const headers = screen.getAllByRole("columnheader");
    expect(headers.map((h) => h.textContent)).toEqual(["#", "White", "Black"]);
  });

  it("groups moves into rows by move number", () => {
    const moves = makeMoves(4); // 1. move1 move2  2. move3 move4
    render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);

    const rows = screen.getAllByRole("row").slice(1); // skip header row
    expect(rows).toHaveLength(2);

    // Row 1: move number 1, White = move1, Black = move2
    expect(within(rows[0]).getByText("1")).toBeInTheDocument();
    expect(within(rows[0]).getByText("move1")).toBeInTheDocument();
    expect(within(rows[0]).getByText("move2")).toBeInTheDocument();

    // Row 2: move number 2, White = move3, Black = move4
    expect(within(rows[1]).getByText("2")).toBeInTheDocument();
    expect(within(rows[1]).getByText("move3")).toBeInTheDocument();
    expect(within(rows[1]).getByText("move4")).toBeInTheDocument();
  });

  it("handles odd number of moves (last row has only White)", () => {
    const moves = makeMoves(3); // 1. move1 move2  2. move3 (no Black)
    render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[1]).getByText("move3")).toBeInTheDocument();
    // The Black cell for row 2 should be empty
    expect(within(rows[1]).queryByTestId("move-cell-3")).not.toBeInTheDocument();
  });

  it("highlights the current move", () => {
    const moves = makeMoves(4);
    render(<MoveList moves={moves} currentMove={1} onSelect={vi.fn()} />);

    const activeCell = screen.getByTestId("move-cell-1");
    expect(activeCell).toHaveClass("move-list-cell-move--active");
    expect(activeCell).toHaveAttribute("aria-current", "true");

    // Other cells should not be active
    const otherCell = screen.getByTestId("move-cell-0");
    expect(otherCell).not.toHaveClass("move-list-cell-move--active");
    expect(otherCell).not.toHaveAttribute("aria-current");
  });

  it("calls onSelect with correct move index on click", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const moves = makeMoves(4);
    render(<MoveList moves={moves} currentMove={0} onSelect={onSelect} />);

    await user.click(screen.getByTestId("move-cell-2"));
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("calls onSelect on Enter key press", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const moves = makeMoves(4);
    render(<MoveList moves={moves} currentMove={0} onSelect={onSelect} />);

    const cell = screen.getByTestId("move-cell-3");
    cell.focus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith(3);
  });

  it("calls onSelect on Space key press", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const moves = makeMoves(4);
    render(<MoveList moves={moves} currentMove={0} onSelect={onSelect} />);

    const cell = screen.getByTestId("move-cell-1");
    cell.focus();
    await user.keyboard(" ");
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  // ---------------------------------------------------------------------------
  // Classification indicators — 6 distinct icons
  // ---------------------------------------------------------------------------

  describe("classification indicators", () => {
    const classifications: { classification: MoveClassification; icon: string }[] = [
      { classification: "best", icon: "★" },
      { classification: "excellent", icon: "◆" },
      { classification: "good", icon: "●" },
      { classification: "inaccuracy", icon: "▲" },
      { classification: "mistake", icon: "■" },
      { classification: "blunder", icon: "✖" },
    ];

    it.each(classifications)(
      "shows $classification icon ($icon) for $classification moves",
      ({ classification, icon }) => {
        const moves = [
          makeMove({
            move_number: 1,
            is_white: true,
            move_san: "e4",
            classification,
          }),
        ];
        render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
        const indicator = screen.getByTestId(`classification-${classification}`);
        expect(indicator).toBeInTheDocument();
        expect(indicator.textContent).toBe(icon);
      },
    );

    it("all 6 classification icons are unique", () => {
      const icons = classifications.map((c) => c.icon);
      expect(new Set(icons).size).toBe(6);
    });

    it("all 6 classification icons have unique colors via CSS classes", () => {
      // Render all 6 classifications at once
      const moves = classifications.map((c, i) =>
        makeMove({
          move_number: Math.floor(i / 2) + 1,
          is_white: i % 2 === 0,
          move_san: `move${i}`,
          classification: c.classification,
        }),
      );
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);

      const classes = classifications.map((c) => {
        const el = screen.getByTestId(`classification-${c.classification}`);
        return el.className;
      });

      // Each should have a unique CSS class modifier
      expect(new Set(classes).size).toBe(6);
    });
  });

  // ---------------------------------------------------------------------------
  // Classification unavailable (Requirement 6.5)
  // ---------------------------------------------------------------------------

  describe("classification unavailable", () => {
    it("shows unavailable indicator when classification is null", () => {
      const moves = [
        makeMove({
          move_number: 1,
          is_white: true,
          move_san: "e4",
          classification: null,
        }),
      ];
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      const indicator = screen.getByTestId("classification-unavailable");
      expect(indicator).toBeInTheDocument();
      expect(indicator.textContent).toBe("?");
      expect(indicator).toHaveAttribute("title", "Classification unavailable");
    });

    it("shows unavailable for some moves and classification for others", () => {
      const moves = [
        makeMove({
          move_number: 1,
          is_white: true,
          move_san: "e4",
          classification: "best",
        }),
        makeMove({
          move_number: 1,
          is_white: false,
          move_san: "e5",
          classification: null,
        }),
      ];
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      expect(screen.getByTestId("classification-best")).toBeInTheDocument();
      expect(screen.getByTestId("classification-unavailable")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Accessibility
  // ---------------------------------------------------------------------------

  describe("accessibility", () => {
    it("has grid role on the table", () => {
      const moves = makeMoves(2);
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      expect(screen.getByRole("grid")).toBeInTheDocument();
    });

    it("move cells are focusable via tabIndex", () => {
      const moves = makeMoves(2);
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      const cell = screen.getByTestId("move-cell-0");
      expect(cell).toHaveAttribute("tabindex", "0");
    });

    it("classification icons have aria-label", () => {
      const moves = [
        makeMove({
          move_number: 1,
          is_white: true,
          move_san: "e4",
          classification: "blunder",
        }),
      ];
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      expect(screen.getByLabelText("blunder move")).toBeInTheDocument();
    });

    it("unavailable indicator has aria-label", () => {
      const moves = [
        makeMove({
          move_number: 1,
          is_white: true,
          move_san: "e4",
          classification: null,
        }),
      ];
      render(<MoveList moves={moves} currentMove={0} onSelect={vi.fn()} />);
      expect(
        screen.getByLabelText("Classification unavailable"),
      ).toBeInTheDocument();
    });
  });
});
