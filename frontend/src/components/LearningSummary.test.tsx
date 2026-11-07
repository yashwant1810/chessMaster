import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import LearningSummary from "./LearningSummary";
import type { LearningInsight, MoveClassification } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeInsight(
  overrides?: Partial<LearningInsight>,
): LearningInsight {
  return {
    move_number: 10,
    is_white: true,
    played_move: "Nf3",
    best_move: "e4",
    centipawn_loss: 45,
    classification: "inaccuracy" as MoveClassification,
    principal_variation: ["e4", "e5", "Nf3"],
    explanation: "The knight move allows Black to equalize.",
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe("LearningSummary", () => {
  describe("when insights list is empty", () => {
    it("renders the panel with a congratulatory message", () => {
      render(<LearningSummary insights={[]} />);
      expect(screen.getByTestId("learning-summary")).toBeInTheDocument();
      expect(screen.getByTestId("learning-summary-empty")).toBeInTheDocument();
      expect(
        screen.getByText("No suboptimal moves found. Great game!"),
      ).toBeInTheDocument();
    });

    it("does not render the list", () => {
      render(<LearningSummary insights={[]} />);
      expect(screen.queryByTestId("learning-summary-list")).not.toBeInTheDocument();
    });

    it("renders the title", () => {
      render(<LearningSummary insights={[]} />);
      expect(screen.getByText("Learning Summary")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Rendering all suboptimal moves (Requirement 9.4)
  // ---------------------------------------------------------------------------

  describe("listing suboptimal moves", () => {
    it("renders one item per insight", () => {
      const insights = [
        makeInsight({ move_number: 5, classification: "inaccuracy" as MoveClassification }),
        makeInsight({ move_number: 12, is_white: false, classification: "mistake" as MoveClassification }),
        makeInsight({ move_number: 20, classification: "blunder" as MoveClassification }),
      ];
      render(<LearningSummary insights={insights} />);
      const list = screen.getByTestId("learning-summary-list");
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(3);
    });

    it("displays classification badge for each insight", () => {
      const insights = [
        makeInsight({ move_number: 3, classification: "inaccuracy" as MoveClassification }),
        makeInsight({ move_number: 7, classification: "mistake" as MoveClassification }),
        makeInsight({ move_number: 15, classification: "blunder" as MoveClassification }),
      ];
      render(<LearningSummary insights={insights} />);

      expect(screen.getByTestId("learning-summary-badge-0")).toHaveTextContent("inaccuracy");
      expect(screen.getByTestId("learning-summary-badge-1")).toHaveTextContent("mistake");
      expect(screen.getByTestId("learning-summary-badge-2")).toHaveTextContent("blunder");
    });

    it("displays badge CSS classes correctly", () => {
      const insights = [
        makeInsight({ move_number: 3, classification: "inaccuracy" as MoveClassification }),
        makeInsight({ move_number: 7, classification: "mistake" as MoveClassification }),
        makeInsight({ move_number: 15, classification: "blunder" as MoveClassification }),
      ];
      render(<LearningSummary insights={insights} />);

      expect(screen.getByTestId("learning-summary-badge-0")).toHaveClass(
        "learning-summary-badge--inaccuracy",
      );
      expect(screen.getByTestId("learning-summary-badge-1")).toHaveClass(
        "learning-summary-badge--mistake",
      );
      expect(screen.getByTestId("learning-summary-badge-2")).toHaveClass(
        "learning-summary-badge--blunder",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Move labels
  // ---------------------------------------------------------------------------

  describe("move labels", () => {
    it("formats White move as 'N. move'", () => {
      render(
        <LearningSummary
          insights={[makeInsight({ move_number: 8, is_white: true, played_move: "Bb5" })]}
        />,
      );
      expect(screen.getByTestId("learning-summary-move-0")).toHaveTextContent("8. Bb5");
    });

    it("formats Black move as 'N... move'", () => {
      render(
        <LearningSummary
          insights={[makeInsight({ move_number: 14, is_white: false, played_move: "Qd7" })]}
        />,
      );
      expect(screen.getByTestId("learning-summary-move-0")).toHaveTextContent("14... Qd7");
    });
  });

  // ---------------------------------------------------------------------------
  // Centipawn loss
  // ---------------------------------------------------------------------------

  describe("centipawn loss", () => {
    it("displays centipawn loss for each insight", () => {
      render(
        <LearningSummary
          insights={[
            makeInsight({ centipawn_loss: 55 }),
            makeInsight({ move_number: 15, centipawn_loss: 220 }),
          ]}
        />,
      );
      expect(screen.getByTestId("learning-summary-cp-loss-0")).toHaveTextContent("55 cp");
      expect(screen.getByTestId("learning-summary-cp-loss-1")).toHaveTextContent("220 cp");
    });
  });

  // ---------------------------------------------------------------------------
  // Best move suggestion
  // ---------------------------------------------------------------------------

  describe("best move", () => {
    it("displays the best move for each insight", () => {
      render(
        <LearningSummary
          insights={[
            makeInsight({ best_move: "d4" }),
            makeInsight({ move_number: 20, best_move: "Rc1" }),
          ]}
        />,
      );
      expect(screen.getByTestId("learning-summary-best-move-0")).toHaveTextContent("Best: d4");
      expect(screen.getByTestId("learning-summary-best-move-1")).toHaveTextContent("Best: Rc1");
    });
  });

  // ---------------------------------------------------------------------------
  // Explanation text
  // ---------------------------------------------------------------------------

  describe("explanation", () => {
    it("displays explanations for each insight", () => {
      const explanation1 = "Allows a tactical shot.";
      const explanation2 = "Loses a piece due to a fork.";
      render(
        <LearningSummary
          insights={[
            makeInsight({ explanation: explanation1 }),
            makeInsight({ move_number: 20, explanation: explanation2 }),
          ]}
        />,
      );
      expect(screen.getByTestId("learning-summary-explanation-0")).toHaveTextContent(explanation1);
      expect(screen.getByTestId("learning-summary-explanation-1")).toHaveTextContent(explanation2);
    });
  });

  // ---------------------------------------------------------------------------
  // Click navigation (onMoveClick callback)
  // ---------------------------------------------------------------------------

  describe("move click navigation", () => {
    it("calls onMoveClick with correct move_number and is_white", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      const insights = [
        makeInsight({ move_number: 5, is_white: true }),
        makeInsight({ move_number: 12, is_white: false }),
      ];

      render(<LearningSummary insights={insights} onMoveClick={handleClick} />);

      await user.click(screen.getByTestId("learning-summary-item-0"));
      expect(handleClick).toHaveBeenCalledWith(5, true);

      await user.click(screen.getByTestId("learning-summary-item-1"));
      expect(handleClick).toHaveBeenCalledWith(12, false);
    });

    it("makes items clickable when onMoveClick is provided", () => {
      render(
        <LearningSummary
          insights={[makeInsight()]}
          onMoveClick={() => {}}
        />,
      );
      const item = screen.getByTestId("learning-summary-item-0");
      expect(item).toHaveClass("learning-summary-item--clickable");
      expect(item).toHaveAttribute("role", "button");
      expect(item).toHaveAttribute("tabindex", "0");
    });

    it("does not make items clickable when onMoveClick is absent", () => {
      render(<LearningSummary insights={[makeInsight()]} />);
      const item = screen.getByTestId("learning-summary-item-0");
      expect(item).not.toHaveClass("learning-summary-item--clickable");
      expect(item).not.toHaveAttribute("role");
    });

    it("supports keyboard activation with Enter", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <LearningSummary
          insights={[makeInsight({ move_number: 7, is_white: true })]}
          onMoveClick={handleClick}
        />,
      );

      const item = screen.getByTestId("learning-summary-item-0");
      item.focus();
      await user.keyboard("{Enter}");
      expect(handleClick).toHaveBeenCalledWith(7, true);
    });

    it("supports keyboard activation with Space", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      render(
        <LearningSummary
          insights={[makeInsight({ move_number: 9, is_white: false })]}
          onMoveClick={handleClick}
        />,
      );

      const item = screen.getByTestId("learning-summary-item-0");
      item.focus();
      await user.keyboard(" ");
      expect(handleClick).toHaveBeenCalledWith(9, false);
    });
  });

  // ---------------------------------------------------------------------------
  // Border color per classification
  // ---------------------------------------------------------------------------

  describe("item border colors", () => {
    it("applies inaccuracy border class", () => {
      render(
        <LearningSummary
          insights={[makeInsight({ classification: "inaccuracy" as MoveClassification })]}
        />,
      );
      expect(screen.getByTestId("learning-summary-item-0")).toHaveClass(
        "learning-summary-item--inaccuracy",
      );
    });

    it("applies mistake border class", () => {
      render(
        <LearningSummary
          insights={[makeInsight({ classification: "mistake" as MoveClassification })]}
        />,
      );
      expect(screen.getByTestId("learning-summary-item-0")).toHaveClass(
        "learning-summary-item--mistake",
      );
    });

    it("applies blunder border class", () => {
      render(
        <LearningSummary
          insights={[makeInsight({ classification: "blunder" as MoveClassification })]}
        />,
      );
      expect(screen.getByTestId("learning-summary-item-0")).toHaveClass(
        "learning-summary-item--blunder",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Full integration
  // ---------------------------------------------------------------------------

  describe("full list display", () => {
    it("renders a complete list of mixed insights", () => {
      const insights = [
        makeInsight({
          move_number: 8,
          is_white: true,
          played_move: "Bg5",
          best_move: "Nf3",
          centipawn_loss: 35,
          classification: "inaccuracy" as MoveClassification,
          explanation: "Pins the knight but allows d5 break.",
        }),
        makeInsight({
          move_number: 15,
          is_white: false,
          played_move: "h6",
          best_move: "Rc8",
          centipawn_loss: 150,
          classification: "mistake" as MoveClassification,
          explanation: "Weakens the kingside pawn structure.",
        }),
        makeInsight({
          move_number: 22,
          is_white: true,
          played_move: "Qxa7",
          best_move: "Rd1",
          centipawn_loss: 400,
          classification: "blunder" as MoveClassification,
          explanation: "The queen is trapped after Nb6.",
        }),
      ];

      render(<LearningSummary insights={insights} />);

      // Check all items rendered
      const list = screen.getByTestId("learning-summary-list");
      expect(within(list).getAllByRole("listitem")).toHaveLength(3);

      // Spot check item 1 (mistake)
      expect(screen.getByTestId("learning-summary-badge-1")).toHaveTextContent("mistake");
      expect(screen.getByTestId("learning-summary-move-1")).toHaveTextContent("15... h6");
      expect(screen.getByTestId("learning-summary-cp-loss-1")).toHaveTextContent("150 cp");
      expect(screen.getByTestId("learning-summary-best-move-1")).toHaveTextContent("Best: Rc8");
      expect(screen.getByTestId("learning-summary-explanation-1")).toHaveTextContent(
        "Weakens the kingside pawn structure.",
      );
    });
  });
});
