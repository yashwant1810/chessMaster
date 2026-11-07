import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import "./PerformanceGraph.css";

export interface PerformanceGraphProps {
  /** Cumulative performance rating after each White move. */
  whiteRatings: number[];
  /** Cumulative performance rating after each Black move. */
  blackRatings: number[];
  /** Current half-move index (0 = initial position). */
  currentMove: number;
}

/** A single data point on the performance graph. */
export interface ChartDataPoint {
  moveNumber: number;
  white?: number;
  black?: number;
}

/**
 * Transform per-player rating arrays into Recharts-compatible data points.
 *
 * Each index in the input arrays corresponds to the player's Nth move,
 * so `whiteRatings[0]` is the rating after White's 1st move (move 1),
 * `blackRatings[0]` is the rating after Black's 1st move (move 1), etc.
 */
export function buildChartData(
  whiteRatings: number[],
  blackRatings: number[],
): ChartDataPoint[] {
  const maxLen = Math.max(whiteRatings.length, blackRatings.length);
  const data: ChartDataPoint[] = [];
  for (let i = 0; i < maxLen; i++) {
    data.push({
      moveNumber: i + 1,
      white: i < whiteRatings.length ? whiteRatings[i] : undefined,
      black: i < blackRatings.length ? blackRatings[i] : undefined,
    });
  }
  return data;
}

/**
 * Convert a half-move index to a move number for the X-axis.
 *
 * Half-move 1 → move 1 (White), half-move 2 → move 1 (Black),
 * half-move 3 → move 2 (White), etc.
 */
export function halfMoveToMoveNumber(halfMove: number): number {
  if (halfMove <= 0) return 0;
  return Math.ceil(halfMove / 2);
}

/** White line color — warm amber, solid. */
const WHITE_COLOR = "#d4a44e";
/** Black line color — dark gray, dashed. */
const BLACK_COLOR = "#374151";

/**
 * Line chart of mid-game performance ratings for both players.
 *
 * Plots cumulative performance rating (Y-axis, range 0–3000) against
 * move number (X-axis). White is drawn with a solid line in a light
 * color and Black with a dashed line in a dark color. A reference
 * line marks the current move position.
 *
 * Requirement 8.2
 */
export default function PerformanceGraph({
  whiteRatings,
  blackRatings,
  currentMove,
}: PerformanceGraphProps) {
  const data = buildChartData(whiteRatings, blackRatings);
  const currentMoveNumber = halfMoveToMoveNumber(currentMove);

  if (data.length === 0) {
    return (
      <div className="performance-graph" data-testid="performance-graph">
        <h3 className="performance-graph__title">Performance Rating</h3>
        <p
          className="performance-graph__empty"
          data-testid="performance-graph-empty"
        >
          No performance data available.
        </p>
      </div>
    );
  }

  return (
    <div className="performance-graph" data-testid="performance-graph">
      <h3 className="performance-graph__title">Performance Rating</h3>
      <div
        className="performance-graph__chart"
        data-testid="performance-graph-chart"
      >
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{ top: 10, right: 20, bottom: 5, left: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="moveNumber"
              type="number"
              domain={[1, "dataMax"]}
              allowDecimals={false}
              label={{
                value: "Move",
                position: "insideBottomRight",
                offset: -5,
              }}
            />
            <YAxis
              domain={[0, 3000]}
              label={{
                value: "Rating",
                angle: -90,
                position: "insideLeft",
                offset: 10,
              }}
            />
            <Tooltip
              formatter={(value, name) => [
                value,
                name === "white" ? "White" : "Black",
              ]}
              labelFormatter={(label) => `Move ${label}`}
            />
            <Legend />
            {currentMoveNumber > 0 && currentMoveNumber <= data.length && (
              <ReferenceLine
                x={currentMoveNumber}
                stroke="#888"
                strokeDasharray="4 4"
                label={{
                  value: "▼",
                  position: "top",
                  fill: "#888",
                  fontSize: 14,
                }}
              />
            )}
            <Line
              type="monotone"
              dataKey="white"
              name="White"
              stroke={WHITE_COLOR}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
            <Line
              type="monotone"
              dataKey="black"
              name="Black"
              stroke={BLACK_COLOR}
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
