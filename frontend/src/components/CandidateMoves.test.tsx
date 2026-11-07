import { render, screen, within } from "@testing-library/react";
import CandidateMoves from "./CandidateMoves";
import type { CandidateMove } from "../types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeCandidate(
  overrides: Partial<CandidateMove> & { move_san: string },
): CandidateMove {
  return {
    evaluation: 0,
    mate_in: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Basic rendering
// ---------------------------------------------------------------------------

describe("CandidateMoves", () => {
  it("renders the component with heading", () => {
    render(
      <CandidateMoves
        candidates={[makeCandidate({ move_san: "e4", evaluation: 30 })]}
        playerMove="e4"
        playerEvaluation={30}
        playerMateIn={null}
      />,
    );
    expect(screen.getByText("Candidate Moves")).toBeInTheDocument();
    expect(screen.getByTestId("candidate-moves")).toBeInTheDocument();
  });

  it("renders empty state when no candidates", () => {
    render(
      <CandidateMoves
        candidates={[]}
        playerMove="e4"
        playerEvaluation={10}
        playerMateIn={null}
      />,
    );
    expect(screen.getByTestId("candidate-moves-empty")).toBeInTheDocument();
    expect(screen.getByText("No candidate moves available.")).toBeInTheDocument();
    expect(screen.queryByTestId("candidate-moves-list")).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------------
  // Display up to 3 candidates (Requirement 7.1)
  // ---------------------------------------------------------------------------

  describe("candidate count", () => {
    it("displays all candidates when there are fewer than 3", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="c4"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );
      const list = screen.getByTestId("candidate-moves-list");
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(2);
    });

    it("displays exactly 3 candidates when there are 3", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
        makeCandidate({ move_san: "c4", evaluation: 10 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Nf3"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );
      const list = screen.getByTestId("candidate-moves-list");
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(3);
    });

    it("limits to 3 candidates when more are provided", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
        makeCandidate({ move_san: "c4", evaluation: 10 }),
        makeCandidate({ move_san: "Nf3", evaluation: 5 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Nf3"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );
      const list = screen.getByTestId("candidate-moves-list");
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(3);
    });

    it("displays 1 candidate for a single legal move", () => {
      const candidates = [makeCandidate({ move_san: "Kh1", evaluation: -500 })];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Kh1"
          playerEvaluation={-500}
          playerMateIn={null}
        />,
      );
      const list = screen.getByTestId("candidate-moves-list");
      const items = within(list).getAllByRole("listitem");
      expect(items).toHaveLength(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Descending evaluation order
  // ---------------------------------------------------------------------------

  describe("sorting order", () => {
    it("displays candidates in descending evaluation order", () => {
      const candidates = [
        makeCandidate({ move_san: "c4", evaluation: 10 }),
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Nf3"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );

      const item0 = screen.getByTestId("candidate-move-0");
      const item1 = screen.getByTestId("candidate-move-1");
      const item2 = screen.getByTestId("candidate-move-2");

      expect(within(item0).getByText("e4")).toBeInTheDocument();
      expect(within(item1).getByText("d4")).toBeInTheDocument();
      expect(within(item2).getByText("c4")).toBeInTheDocument();
    });

    it("ranks mate-in candidates above centipawn candidates", () => {
      const candidates = [
        makeCandidate({ move_san: "Qf7", evaluation: null, mate_in: 2 }),
        makeCandidate({ move_san: "e4", evaluation: 500 }),
        makeCandidate({ move_san: "d4", evaluation: 300 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="d4"
          playerEvaluation={300}
          playerMateIn={null}
        />,
      );

      const item0 = screen.getByTestId("candidate-move-0");
      expect(within(item0).getByText("Qf7")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Centipawn evaluation display (Requirement 7.3)
  // ---------------------------------------------------------------------------

  describe("evaluation display", () => {
    it("shows centipawn evaluation for each candidate", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: -15 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="c4"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("+30");
      expect(screen.getByTestId("candidate-eval-1")).toHaveTextContent("-15");
    });

    it("formats positive evaluations with + prefix", () => {
      render(
        <CandidateMoves
          candidates={[makeCandidate({ move_san: "e4", evaluation: 100 })]}
          playerMove="d4"
          playerEvaluation={50}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("+100");
    });

    it("formats zero evaluation without sign", () => {
      render(
        <CandidateMoves
          candidates={[makeCandidate({ move_san: "e4", evaluation: 0 })]}
          playerMove="d4"
          playerEvaluation={0}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("0");
    });

    it("formats mate-in-N evaluations", () => {
      render(
        <CandidateMoves
          candidates={[
            makeCandidate({ move_san: "Qf7", evaluation: null, mate_in: 3 }),
          ]}
          playerMove="d4"
          playerEvaluation={50}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("M+3");
    });

    it("formats negative mate-in (Black mating)", () => {
      render(
        <CandidateMoves
          candidates={[
            makeCandidate({ move_san: "Qf2", evaluation: null, mate_in: -2 }),
          ]}
          playerMove="d4"
          playerEvaluation={50}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("M-2");
    });

    it("shows en-dash for null evaluations", () => {
      render(
        <CandidateMoves
          candidates={[
            makeCandidate({ move_san: "e4", evaluation: null, mate_in: null }),
          ]}
          playerMove="d4"
          playerEvaluation={null}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("candidate-eval-0")).toHaveTextContent("–");
    });

    it("shows player move evaluation in separate section", () => {
      render(
        <CandidateMoves
          candidates={[makeCandidate({ move_san: "e4", evaluation: 30 })]}
          playerMove="d4"
          playerEvaluation={15}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("player-move-eval")).toHaveTextContent("+15");
    });

    it("shows player move mate-in evaluation", () => {
      render(
        <CandidateMoves
          candidates={[makeCandidate({ move_san: "e4", evaluation: 30 })]}
          playerMove="Qh7"
          playerEvaluation={null}
          playerMateIn={1}
        />,
      );
      expect(screen.getByTestId("player-move-eval")).toHaveTextContent("M+1");
    });
  });

  // ---------------------------------------------------------------------------
  // Player move marking (Requirement 7.4)
  // ---------------------------------------------------------------------------

  describe("player move marking", () => {
    it("marks the player's move in the candidate list with a badge", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
        makeCandidate({ move_san: "c4", evaluation: 10 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="d4"
          playerEvaluation={20}
          playerMateIn={null}
        />,
      );
      // d4 should be at index 1 (sorted descending: e4=30, d4=20, c4=10)
      expect(screen.getByTestId("candidate-player-badge-1")).toBeInTheDocument();
      expect(screen.getByTestId("candidate-player-badge-1")).toHaveTextContent("You");
    });

    it("applies highlight class to the player's move item", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="e4"
          playerEvaluation={30}
          playerMateIn={null}
        />,
      );
      const item = screen.getByTestId("candidate-move-0");
      expect(item).toHaveClass("candidate-move-item--player");
    });

    it("does not mark non-player moves", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="e4"
          playerEvaluation={30}
          playerMateIn={null}
        />,
      );
      expect(screen.queryByTestId("candidate-player-badge-1")).not.toBeInTheDocument();
      const item1 = screen.getByTestId("candidate-move-1");
      expect(item1).not.toHaveClass("candidate-move-item--player");
    });

    it("hides player-move section when player's move is in candidates", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="e4"
          playerEvaluation={30}
          playerMateIn={null}
        />,
      );
      expect(screen.queryByTestId("player-move-section")).not.toBeInTheDocument();
    });

    it("shows player-move section when player's move is NOT in candidates", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Nf3"
          playerEvaluation={10}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("player-move-section")).toBeInTheDocument();
      expect(screen.getByText("Nf3")).toBeInTheDocument();
      expect(screen.getByTestId("player-move-eval")).toHaveTextContent("+10");
    });

    it("shows player-move section with en-dash for null evaluation", () => {
      render(
        <CandidateMoves
          candidates={[makeCandidate({ move_san: "e4", evaluation: 30 })]}
          playerMove="a3"
          playerEvaluation={null}
          playerMateIn={null}
        />,
      );
      expect(screen.getByTestId("player-move-eval")).toHaveTextContent("–");
    });
  });

  // ---------------------------------------------------------------------------
  // Rank numbering
  // ---------------------------------------------------------------------------

  describe("rank numbering", () => {
    it("shows rank numbers 1, 2, 3 for candidates", () => {
      const candidates = [
        makeCandidate({ move_san: "e4", evaluation: 30 }),
        makeCandidate({ move_san: "d4", evaluation: 20 }),
        makeCandidate({ move_san: "c4", evaluation: 10 }),
      ];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="Nf3"
          playerEvaluation={5}
          playerMateIn={null}
        />,
      );
      const item0 = screen.getByTestId("candidate-move-0");
      const item1 = screen.getByTestId("candidate-move-1");
      const item2 = screen.getByTestId("candidate-move-2");

      expect(within(item0).getByText("1")).toBeInTheDocument();
      expect(within(item1).getByText("2")).toBeInTheDocument();
      expect(within(item2).getByText("3")).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Accessibility
  // ---------------------------------------------------------------------------

  describe("accessibility", () => {
    it("player badge has aria-label", () => {
      const candidates = [makeCandidate({ move_san: "e4", evaluation: 30 })];
      render(
        <CandidateMoves
          candidates={candidates}
          playerMove="e4"
          playerEvaluation={30}
          playerMateIn={null}
        />,
      );
      expect(screen.getByLabelText("Player's move")).toBeInTheDocument();
    });
  });
});
