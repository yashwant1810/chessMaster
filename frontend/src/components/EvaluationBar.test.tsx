import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EvaluationBar, {
  computeWhitePercent,
  formatEvaluation,
} from "./EvaluationBar";

// ---------------------------------------------------------------------------
// Unit tests for computeWhitePercent
// ---------------------------------------------------------------------------

describe("computeWhitePercent", () => {
  it("returns 50 for an even position (evaluation = 0)", () => {
    expect(computeWhitePercent(0, null)).toBe(50);
  });

  it("returns > 50 for White advantage (positive evaluation)", () => {
    expect(computeWhitePercent(200, null)).toBeGreaterThan(50);
  });

  it("returns < 50 for Black advantage (negative evaluation)", () => {
    expect(computeWhitePercent(-200, null)).toBeLessThan(50);
  });

  it("clamps at 100 for evaluation >= +2000", () => {
    expect(computeWhitePercent(2000, null)).toBe(100);
    expect(computeWhitePercent(5000, null)).toBe(100);
  });

  it("clamps at 0 for evaluation <= -2000", () => {
    expect(computeWhitePercent(-2000, null)).toBe(0);
    expect(computeWhitePercent(-5000, null)).toBe(0);
  });

  it("returns 100 when White has checkmate (mateIn > 0)", () => {
    expect(computeWhitePercent(null, 3)).toBe(100);
    expect(computeWhitePercent(null, 1)).toBe(100);
  });

  it("returns 0 when Black has checkmate (mateIn < 0)", () => {
    expect(computeWhitePercent(null, -3)).toBe(0);
    expect(computeWhitePercent(null, -1)).toBe(0);
  });

  it("prefers mateIn over evaluation when both are provided", () => {
    // Even though evaluation is 0, mateIn should dominate
    expect(computeWhitePercent(0, 2)).toBe(100);
    expect(computeWhitePercent(500, -1)).toBe(0);
  });

  it("returns 50 when evaluation is null and no mate", () => {
    expect(computeWhitePercent(null, null)).toBe(50);
  });

  it("maps +1000 to 75%", () => {
    // (+1000 + 2000) / (2 * 2000) * 100 = 3000/4000 * 100 = 75
    expect(computeWhitePercent(1000, null)).toBe(75);
  });

  it("maps -1000 to 25%", () => {
    expect(computeWhitePercent(-1000, null)).toBe(25);
  });
});

// ---------------------------------------------------------------------------
// Unit tests for formatEvaluation
// ---------------------------------------------------------------------------

describe("formatEvaluation", () => {
  it("formats checkmate as M followed by move count", () => {
    expect(formatEvaluation(null, 3)).toBe("M3");
    expect(formatEvaluation(null, -5)).toBe("M5");
  });

  it("formats positive evaluation with + sign", () => {
    expect(formatEvaluation(150, null)).toBe("+1.5");
  });

  it("formats negative evaluation with - sign", () => {
    expect(formatEvaluation(-250, null)).toBe("-2.5");
  });

  it("formats zero evaluation", () => {
    expect(formatEvaluation(0, null)).toBe("+0.0");
  });

  it("returns dash for null evaluation with no mate", () => {
    expect(formatEvaluation(null, null)).toBe("–");
  });
});

// ---------------------------------------------------------------------------
// Component rendering tests
// ---------------------------------------------------------------------------

describe("EvaluationBar component", () => {
  it("renders with correct test IDs", () => {
    render(<EvaluationBar evaluation={0} mateIn={null} />);

    expect(screen.getByTestId("evaluation-bar")).toBeInTheDocument();
    expect(screen.getByTestId("eval-bar-black")).toBeInTheDocument();
    expect(screen.getByTestId("eval-bar-white")).toBeInTheDocument();
  });

  it("sets ARIA attributes for accessibility", () => {
    render(<EvaluationBar evaluation={150} mateIn={null} />);

    const bar = screen.getByTestId("evaluation-bar");
    expect(bar).toHaveAttribute("role", "meter");
    expect(bar).toHaveAttribute(
      "aria-label",
      "Position evaluation: +1.5",
    );
  });

  it("renders white section at 50% for even position", () => {
    render(<EvaluationBar evaluation={0} mateIn={null} />);

    const whiteSection = screen.getByTestId("eval-bar-white");
    expect(whiteSection.style.height).toBe("50%");
  });

  it("renders white section at 100% for White checkmate", () => {
    render(<EvaluationBar evaluation={null} mateIn={2} />);

    const whiteSection = screen.getByTestId("eval-bar-white");
    expect(whiteSection.style.height).toBe("100%");
  });

  it("renders white section at 0% for Black checkmate", () => {
    render(<EvaluationBar evaluation={null} mateIn={-2} />);

    const whiteSection = screen.getByTestId("eval-bar-white");
    expect(whiteSection.style.height).toBe("0%");
  });

  it("applies custom height", () => {
    render(<EvaluationBar evaluation={0} mateIn={null} height={400} />);

    const bar = screen.getByTestId("evaluation-bar");
    expect(bar.style.height).toBe("400px");
  });

  it("displays the evaluation label", () => {
    render(<EvaluationBar evaluation={250} mateIn={null} />);

    expect(screen.getByText("+2.5")).toBeInTheDocument();
  });

  it("displays mate label for checkmate positions", () => {
    render(<EvaluationBar evaluation={null} mateIn={3} />);

    expect(screen.getByText("M3")).toBeInTheDocument();
  });
});
