import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PerformanceGraph, {
  buildChartData,
  halfMoveToMoveNumber,
} from "./PerformanceGraph";

// ---------------------------------------------------------------------------
// Recharts uses ResizeObserver + getBoundingClientRect, neither of which
// exist in jsdom. Mock ResponsiveContainer to render children at a fixed size.
// ---------------------------------------------------------------------------

vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({
      children,
    }: {
      children: React.ReactElement;
    }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

// ---------------------------------------------------------------------------
// buildChartData — pure function unit tests
// ---------------------------------------------------------------------------

describe("buildChartData", () => {
  it("builds data from equal-length arrays", () => {
    const data = buildChartData([1500, 1600], [1400, 1500]);
    expect(data).toEqual([
      { moveNumber: 1, white: 1500, black: 1400 },
      { moveNumber: 2, white: 1600, black: 1500 },
    ]);
  });

  it("handles White having more moves than Black", () => {
    const data = buildChartData([1500, 1600, 1550], [1400, 1500]);
    expect(data).toEqual([
      { moveNumber: 1, white: 1500, black: 1400 },
      { moveNumber: 2, white: 1600, black: 1500 },
      { moveNumber: 3, white: 1550, black: undefined },
    ]);
  });

  it("handles Black having more moves than White", () => {
    const data = buildChartData([1500], [1400, 1500]);
    expect(data).toEqual([
      { moveNumber: 1, white: 1500, black: 1400 },
      { moveNumber: 2, white: undefined, black: 1500 },
    ]);
  });

  it("returns empty array for empty inputs", () => {
    expect(buildChartData([], [])).toEqual([]);
  });

  it("handles single White data point with no Black data", () => {
    expect(buildChartData([2000], [])).toEqual([
      { moveNumber: 1, white: 2000, black: undefined },
    ]);
  });

  it("handles single Black data point with no White data", () => {
    expect(buildChartData([], [1800])).toEqual([
      { moveNumber: 1, white: undefined, black: 1800 },
    ]);
  });

  it("assigns sequential move numbers starting from 1", () => {
    const data = buildChartData([100, 200, 300, 400, 500], [110, 220, 330, 440, 550]);
    expect(data.map((d) => d.moveNumber)).toEqual([1, 2, 3, 4, 5]);
  });

  it("preserves exact rating values", () => {
    const data = buildChartData([0, 3000], [1, 2999]);
    expect(data[0].white).toBe(0);
    expect(data[0].black).toBe(1);
    expect(data[1].white).toBe(3000);
    expect(data[1].black).toBe(2999);
  });
});

// ---------------------------------------------------------------------------
// halfMoveToMoveNumber — pure function unit tests
// ---------------------------------------------------------------------------

describe("halfMoveToMoveNumber", () => {
  it("returns 0 for half-move 0 (initial position)", () => {
    expect(halfMoveToMoveNumber(0)).toBe(0);
  });

  it("returns 0 for negative values", () => {
    expect(halfMoveToMoveNumber(-1)).toBe(0);
  });

  it("maps half-move 1 to move 1 (White's 1st move)", () => {
    expect(halfMoveToMoveNumber(1)).toBe(1);
  });

  it("maps half-move 2 to move 1 (Black's 1st move)", () => {
    expect(halfMoveToMoveNumber(2)).toBe(1);
  });

  it("maps half-move 3 to move 2 (White's 2nd move)", () => {
    expect(halfMoveToMoveNumber(3)).toBe(2);
  });

  it("maps half-move 4 to move 2 (Black's 2nd move)", () => {
    expect(halfMoveToMoveNumber(4)).toBe(2);
  });

  it("maps half-move 10 to move 5", () => {
    expect(halfMoveToMoveNumber(10)).toBe(5);
  });
});

// ---------------------------------------------------------------------------
// Component rendering tests
// ---------------------------------------------------------------------------

describe("PerformanceGraph", () => {
  // -------------------------------------------------------------------------
  // Empty state (Requirement 8.4 — message when data unavailable)
  // -------------------------------------------------------------------------

  describe("empty state", () => {
    it("shows empty message when both rating arrays are empty", () => {
      render(
        <PerformanceGraph
          whiteRatings={[]}
          blackRatings={[]}
          currentMove={0}
        />,
      );
      expect(screen.getByTestId("performance-graph")).toBeInTheDocument();
      expect(screen.getByTestId("performance-graph-empty")).toBeInTheDocument();
      expect(
        screen.getByText("No performance data available."),
      ).toBeInTheDocument();
    });

    it("does not render chart container when empty", () => {
      render(
        <PerformanceGraph
          whiteRatings={[]}
          blackRatings={[]}
          currentMove={0}
        />,
      );
      expect(
        screen.queryByTestId("performance-graph-chart"),
      ).not.toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // With data — basic rendering
  // -------------------------------------------------------------------------

  describe("with data", () => {
    it("renders the component container and title", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500, 1600]}
          blackRatings={[1400, 1500]}
          currentMove={1}
        />,
      );
      expect(screen.getByTestId("performance-graph")).toBeInTheDocument();
      expect(screen.getByText("Performance Rating")).toBeInTheDocument();
    });

    it("renders chart container when data exists", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500]}
          blackRatings={[1400]}
          currentMove={1}
        />,
      );
      expect(
        screen.getByTestId("performance-graph-chart"),
      ).toBeInTheDocument();
    });

    it("does not show empty message when data exists", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500]}
          blackRatings={[1400]}
          currentMove={1}
        />,
      );
      expect(
        screen.queryByTestId("performance-graph-empty"),
      ).not.toBeInTheDocument();
    });

    it("renders with only White data", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500, 1600]}
          blackRatings={[]}
          currentMove={1}
        />,
      );
      expect(
        screen.getByTestId("performance-graph-chart"),
      ).toBeInTheDocument();
    });

    it("renders with only Black data", () => {
      render(
        <PerformanceGraph
          whiteRatings={[]}
          blackRatings={[1400, 1500]}
          currentMove={2}
        />,
      );
      expect(
        screen.getByTestId("performance-graph-chart"),
      ).toBeInTheDocument();
    });

    it("renders with currentMove at 0 (no reference line)", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500, 1600]}
          blackRatings={[1400, 1500]}
          currentMove={0}
        />,
      );
      expect(
        screen.getByTestId("performance-graph-chart"),
      ).toBeInTheDocument();
    });

    it("renders with large datasets", () => {
      const whiteRatings = Array.from({ length: 40 }, (_, i) => 1500 + i * 10);
      const blackRatings = Array.from({ length: 40 }, (_, i) => 1400 + i * 10);
      render(
        <PerformanceGraph
          whiteRatings={whiteRatings}
          blackRatings={blackRatings}
          currentMove={40}
        />,
      );
      expect(
        screen.getByTestId("performance-graph-chart"),
      ).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Title always visible
  // -------------------------------------------------------------------------

  describe("title", () => {
    it("displays title in empty state", () => {
      render(
        <PerformanceGraph
          whiteRatings={[]}
          blackRatings={[]}
          currentMove={0}
        />,
      );
      expect(screen.getByText("Performance Rating")).toBeInTheDocument();
    });

    it("displays title with data", () => {
      render(
        <PerformanceGraph
          whiteRatings={[1500]}
          blackRatings={[1400]}
          currentMove={1}
        />,
      );
      expect(screen.getByText("Performance Rating")).toBeInTheDocument();
    });
  });
});
