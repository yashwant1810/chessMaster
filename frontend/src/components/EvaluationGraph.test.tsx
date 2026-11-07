import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import EvaluationGraph from "./EvaluationGraph";
import type { EvalDataPoint } from "../utils/evaluationGraph";

// ---------------------------------------------------------------------------
// Recharts renders SVG elements that are hard to query in jsdom. We mock
// Recharts to produce lightweight DOM elements we can test against, while
// the pure utility functions are tested in evaluationGraph.test.ts.
// ---------------------------------------------------------------------------

vi.mock("recharts", async () => {
  const React = await import("react");

  const ResponsiveContainer = ({ children }: { children: React.ReactNode }) =>
    React.createElement("div", { "data-testid": "responsive-container" }, children);

  const LineChart = ({
    children,
    data,
    onClick,
  }: {
    children: React.ReactNode;
    data: unknown[];
    onClick?: (state: unknown) => void;
  }) =>
    React.createElement(
      "div",
      {
        "data-testid": "line-chart",
        "data-point-count": data.length,
        onClick: () => {
          if (onClick && data.length > 0) {
            // Simulate clicking the first data point
            onClick({ activePayload: [{ payload: data[0] }] });
          }
        },
      },
      children,
    );

  const Line = ({ dot, data: _data }: { dot?: React.ReactNode; data?: unknown[] }) => {
    // Render custom dots if provided as a React element
    if (dot && React.isValidElement(dot)) {
      return React.createElement("div", { "data-testid": "line" });
    }
    return React.createElement("div", { "data-testid": "line" });
  };

  const XAxis = () => React.createElement("div", { "data-testid": "x-axis" });
  const YAxis = () => React.createElement("div", { "data-testid": "y-axis" });
  const CartesianGrid = () => React.createElement("div", { "data-testid": "grid" });
  const Tooltip = () => React.createElement("div", { "data-testid": "tooltip" });

  const ReferenceLine = (props: {
    x?: number;
    y?: number;
    "data-testid"?: string;
  }) => {
    const testId =
      props["data-testid"] ??
      (props.x !== undefined ? "reference-line-x" : "reference-line-y");
    return React.createElement("div", {
      "data-testid": testId,
      "data-x": props.x,
      "data-y": props.y,
    });
  };

  return {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
  };
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function makeEval(
  moveIndex: number,
  evaluation: number | null,
  mateIn: number | null = null,
): EvalDataPoint {
  return { moveIndex, evaluation, mateIn };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("EvaluationGraph", () => {
  it("renders the component with title", () => {
    render(
      <EvaluationGraph
        evaluations={[makeEval(0, 50)]}
        currentMove={0}
        onClick={() => {}}
      />,
    );
    expect(screen.getByText("Evaluation")).toBeInTheDocument();
    expect(screen.getByTestId("evaluation-graph")).toBeInTheDocument();
  });

  it("shows empty state when no evaluations are available", () => {
    render(
      <EvaluationGraph evaluations={[]} currentMove={0} onClick={() => {}} />,
    );
    expect(screen.getByTestId("eval-graph-empty")).toBeInTheDocument();
    expect(screen.getByText("No evaluation data available.")).toBeInTheDocument();
  });

  it("shows empty state when all evaluations are null", () => {
    const evals = [makeEval(0, null), makeEval(1, null)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={0} onClick={() => {}} />,
    );
    expect(screen.getByTestId("eval-graph-empty")).toBeInTheDocument();
  });

  it("renders the LineChart when evaluations are available", () => {
    const evals = [makeEval(0, 50), makeEval(1, 100)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={0} onClick={() => {}} />,
    );
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
    expect(screen.queryByTestId("eval-graph-empty")).not.toBeInTheDocument();
  });

  it("passes correct data point count to chart", () => {
    // 3 evals, 1 null → 2 data points
    const evals = [
      makeEval(0, 50),
      makeEval(1, null),
      makeEval(2, 100),
    ];
    render(
      <EvaluationGraph evaluations={evals} currentMove={0} onClick={() => {}} />,
    );
    const chart = screen.getByTestId("line-chart");
    expect(chart.getAttribute("data-point-count")).toBe("2");
  });

  it("calls onClick with moveIndex when chart is clicked", () => {
    const onClick = vi.fn();
    const evals = [makeEval(0, 50), makeEval(1, 100)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={0} onClick={onClick} />,
    );
    // Our mock simulates clicking the first data point
    screen.getByTestId("line-chart").click();
    expect(onClick).toHaveBeenCalledWith(0);
  });

  it("renders current-move reference line when currentMove is in graph data", () => {
    const evals = [makeEval(0, 50), makeEval(1, 100), makeEval(2, 150)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={1} onClick={() => {}} />,
    );
    // The ReferenceLine with data-testid="current-move-indicator" should be rendered
    expect(screen.getByTestId("current-move-indicator")).toBeInTheDocument();
  });

  it("does not render current-move reference line when currentMove is not in graph data", () => {
    // move 1 has null evaluation, so it's not in graph data
    const evals = [makeEval(0, 50), makeEval(1, null), makeEval(2, 150)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={1} onClick={() => {}} />,
    );
    expect(screen.queryByTestId("current-move-indicator")).not.toBeInTheDocument();
  });

  it("renders zero-line reference", () => {
    const evals = [makeEval(0, 50)];
    render(
      <EvaluationGraph evaluations={evals} currentMove={0} onClick={() => {}} />,
    );
    const refLines = screen.getAllByTestId("reference-line-y");
    expect(refLines.length).toBeGreaterThanOrEqual(1);
  });
});
