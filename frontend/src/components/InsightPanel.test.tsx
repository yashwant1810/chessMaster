import { render, screen } from "@testing-library/react";
import InsightPanel from "./InsightPanel";
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
// Empty / cleared state (Requirement 9.5)
// ---------------------------------------------------------------------------

describe("InsightPanel", () => {
  describe("when insight is null (good move)", () => {
    it("renders the panel with a neutral message", () => {
      render(<InsightPanel insight={null} />);
      expect(screen.getByTestId("insight-panel")).toBeInTheDocument();
      expect(screen.getByTestId("insight-panel-empty")).toBeInTheDocument();
      expect(screen.getByText("No issues with this move.")).toBeInTheDocument();
    });

    it("does not render insight content", () => {
      render(<InsightPanel insight={null} />);
      expect(screen.queryByTestId("insight-panel-content")).not.toBeInTheDocument();
    });

    it("renders the title", () => {
      render(<InsightPanel insight={null} />);
      expect(screen.getByText("Move Insight")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Classification badge display (Requirement 9.3)
  // ---------------------------------------------------------------------------

  describe("classification badge", () => {
    it("shows inaccuracy badge", () => {
      render(<InsightPanel insight={makeInsight({ classification: "inaccuracy" as MoveClassification })} />);
      const badge = screen.getByTestId("insight-badge");
      expect(badge).toHaveTextContent("inaccuracy");
      expect(badge).toHaveClass("insight-panel-badge--inaccuracy");
    });

    it("shows mistake badge", () => {
      render(<InsightPanel insight={makeInsight({ classification: "mistake" as MoveClassification })} />);
      const badge = screen.getByTestId("insight-badge");
      expect(badge).toHaveTextContent("mistake");
      expect(badge).toHaveClass("insight-panel-badge--mistake");
    });

    it("shows blunder badge", () => {
      render(<InsightPanel insight={makeInsight({ classification: "blunder" as MoveClassification })} />);
      const badge = screen.getByTestId("insight-badge");
      expect(badge).toHaveTextContent("blunder");
      expect(badge).toHaveClass("insight-panel-badge--blunder");
    });
  });

  // ---------------------------------------------------------------------------
  // Move identification
  // ---------------------------------------------------------------------------

  describe("move identification", () => {
    it("formats White move as 'N. move'", () => {
      render(<InsightPanel insight={makeInsight({ move_number: 5, is_white: true, played_move: "Bb5" })} />);
      expect(screen.getByTestId("insight-move-id")).toHaveTextContent("5. Bb5");
    });

    it("formats Black move as 'N... move'", () => {
      render(<InsightPanel insight={makeInsight({ move_number: 12, is_white: false, played_move: "Qd7" })} />);
      expect(screen.getByTestId("insight-move-id")).toHaveTextContent("12... Qd7");
    });
  });

  // ---------------------------------------------------------------------------
  // Centipawn loss display (Requirement 9.1)
  // ---------------------------------------------------------------------------

  describe("centipawn loss", () => {
    it("displays the centipawn loss value", () => {
      render(<InsightPanel insight={makeInsight({ centipawn_loss: 120 })} />);
      expect(screen.getByTestId("insight-cp-loss")).toBeInTheDocument();
      expect(screen.getByTestId("insight-cp-loss-value")).toHaveTextContent("120");
    });

    it("displays centipawn loss label", () => {
      render(<InsightPanel insight={makeInsight()} />);
      expect(screen.getByText("Centipawn loss:")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Best move display (Requirement 9.2)
  // ---------------------------------------------------------------------------

  describe("best move", () => {
    it("displays the best move in SAN", () => {
      render(<InsightPanel insight={makeInsight({ best_move: "d4" })} />);
      expect(screen.getByTestId("insight-best-move")).toBeInTheDocument();
      expect(screen.getByTestId("insight-best-move-value")).toHaveTextContent("d4");
    });

    it("displays best move label", () => {
      render(<InsightPanel insight={makeInsight()} />);
      expect(screen.getByText("Best move:")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Principal variation display (Requirement 9.2)
  // ---------------------------------------------------------------------------

  describe("principal variation", () => {
    it("displays the PV line as space-separated moves", () => {
      render(
        <InsightPanel
          insight={makeInsight({
            principal_variation: ["d4", "d5", "c4", "e6", "Nc3"],
          })}
        />,
      );
      expect(screen.getByTestId("insight-pv")).toBeInTheDocument();
      expect(screen.getByTestId("insight-pv-moves")).toHaveTextContent(
        "d4 d5 c4 e6 Nc3",
      );
    });

    it("displays the PV label", () => {
      render(<InsightPanel insight={makeInsight()} />);
      expect(screen.getByText("Principal variation:")).toBeInTheDocument();
    });

    it("hides PV section when principal_variation is empty", () => {
      render(
        <InsightPanel
          insight={makeInsight({ principal_variation: [] })}
        />,
      );
      expect(screen.queryByTestId("insight-pv")).not.toBeInTheDocument();
    });

    it("displays single-move PV", () => {
      render(
        <InsightPanel
          insight={makeInsight({ principal_variation: ["Qxd5"] })}
        />,
      );
      expect(screen.getByTestId("insight-pv-moves")).toHaveTextContent("Qxd5");
    });
  });

  // ---------------------------------------------------------------------------
  // Explanation text (Requirement 9.3)
  // ---------------------------------------------------------------------------

  describe("explanation", () => {
    it("displays the explanation text", () => {
      const explanation = "This move loses material due to a tactical oversight.";
      render(<InsightPanel insight={makeInsight({ explanation })} />);
      expect(screen.getByTestId("insight-explanation")).toHaveTextContent(explanation);
    });
  });

  // ---------------------------------------------------------------------------
  // Full integration: all fields displayed together
  // ---------------------------------------------------------------------------

  describe("full insight display", () => {
    it("renders all insight fields for a blunder", () => {
      const insight = makeInsight({
        move_number: 22,
        is_white: false,
        played_move: "Qxa2",
        best_move: "Rc8",
        centipawn_loss: 350,
        classification: "blunder" as MoveClassification,
        principal_variation: ["Rc8", "Rd1", "Qe7"],
        explanation: "Taking the pawn exposes the queen to a discovered attack.",
      });

      render(<InsightPanel insight={insight} />);

      expect(screen.getByTestId("insight-badge")).toHaveTextContent("blunder");
      expect(screen.getByTestId("insight-move-id")).toHaveTextContent("22... Qxa2");
      expect(screen.getByTestId("insight-cp-loss-value")).toHaveTextContent("350");
      expect(screen.getByTestId("insight-best-move-value")).toHaveTextContent("Rc8");
      expect(screen.getByTestId("insight-pv-moves")).toHaveTextContent("Rc8 Rd1 Qe7");
      expect(screen.getByTestId("insight-explanation")).toHaveTextContent(
        "Taking the pawn exposes the queen to a discovered attack.",
      );
    });
  });
});
