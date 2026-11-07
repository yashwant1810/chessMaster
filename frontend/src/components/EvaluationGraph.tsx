import { useMemo, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { EvalDataPoint, GraphDataPoint } from "../utils/evaluationGraph";
import { prepareGraphData, MAX_EVAL } from "../utils/evaluationGraph";
import "./EvaluationGraph.css";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EvaluationGraphProps {
  evaluations: EvalDataPoint[];
  currentMove: number;
  onClick: (moveIndex: number) => void;
}

// ---------------------------------------------------------------------------
// Custom dot renderers
// ---------------------------------------------------------------------------

/** Default (non-critical) data point. */
const NORMAL_DOT_RADIUS = 3;
/** Critical-moment data point. */
const CRITICAL_DOT_RADIUS = 6;

interface DotPayload {
  moveIndex: number;
  clampedEval: number;
  isCritical: boolean;
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: DotPayload;
}

/**
 * Render dots on the line: critical moments get a distinct red diamond
 * while normal points get a small blue circle.
 */
function CustomDot({ cx, cy, payload }: DotProps) {
  if (cx == null || cy == null || !payload) return null;

  if (payload.isCritical) {
    // Diamond shape for critical moments (Requirement 11.3)
    const s = CRITICAL_DOT_RADIUS;
    const points = `${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`;
    return (
      <polygon
        points={points}
        fill="#d32f2f"
        stroke="#b71c1c"
        strokeWidth={1}
        data-testid={`critical-marker-${payload.moveIndex}`}
      />
    );
  }

  return (
    <circle
      cx={cx}
      cy={cy}
      r={NORMAL_DOT_RADIUS}
      fill="#1976d2"
      stroke="#1565c0"
      strokeWidth={1}
      data-testid={`normal-dot-${payload.moveIndex}`}
    />
  );
}

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

interface TooltipPayload {
  payload?: DotPayload;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0].payload;
  if (!data) return null;

  const moveLabel =
    data.moveIndex % 2 === 0
      ? `${Math.floor(data.moveIndex / 2) + 1}. (White)`
      : `${Math.floor(data.moveIndex / 2) + 1}... (Black)`;

  const evalStr =
    data.clampedEval >= 0
      ? `+${(data.clampedEval / 100).toFixed(1)}`
      : `${(data.clampedEval / 100).toFixed(1)}`;

  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #ccc",
        borderRadius: 4,
        padding: "4px 8px",
        fontSize: "0.8rem",
      }}
      data-testid="eval-graph-tooltip"
    >
      <div>{moveLabel}</div>
      <div>Eval: {evalStr}</div>
      {data.isCritical && (
        <div style={{ color: "#d32f2f", fontWeight: 600 }}>Critical moment</div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * EvaluationGraph — line chart of centipawn evaluations vs move number.
 *
 * - Y-axis clamped to ±2000 centipawns (Requirement 11.1)
 * - Click navigates board to nearest move (Requirement 11.2)
 * - Critical moment markers (>100cp swing) (Requirement 11.3)
 * - Position indicator for current move (Requirement 11.4)
 * - Unavailable positions omitted; nearest connected (Requirement 11.5)
 */
export default function EvaluationGraph({
  evaluations,
  currentMove,
  onClick,
}: EvaluationGraphProps) {
  const graphData: GraphDataPoint[] = useMemo(
    () => prepareGraphData(evaluations),
    [evaluations],
  );

  const handleClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (state: any) => {
      if (
        state &&
        state.activePayload &&
        state.activePayload.length > 0 &&
        state.activePayload[0].payload
      ) {
        onClick(state.activePayload[0].payload.moveIndex);
      }
    },
    [onClick],
  );

  if (graphData.length === 0) {
    return (
      <div className="eval-graph" data-testid="evaluation-graph">
        <h3 className="eval-graph__title">Evaluation</h3>
        <p className="eval-graph__empty" data-testid="eval-graph-empty">
          No evaluation data available.
        </p>
      </div>
    );
  }

  // Check if currentMove is within the graph data range
  const currentMoveInGraph = graphData.some(
    (pt) => pt.moveIndex === currentMove,
  );

  return (
    <div className="eval-graph" data-testid="evaluation-graph">
      <h3 className="eval-graph__title">Evaluation</h3>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart
          data={graphData}
          onClick={handleClick}
          margin={{ top: 10, right: 20, bottom: 5, left: 10 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="moveIndex"
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fontSize: 11 }}
            label={{
              value: "Move",
              position: "insideBottomRight",
              offset: -5,
              fontSize: 11,
            }}
          />
          <YAxis
            domain={[-MAX_EVAL, MAX_EVAL]}
            tick={{ fontSize: 11 }}
            label={{
              value: "Eval (cp)",
              angle: -90,
              position: "insideLeft",
              fontSize: 11,
            }}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Zero line (equal position) */}
          <ReferenceLine y={0} stroke="#888" strokeDasharray="4 4" />

          {/* Current move indicator (Requirement 11.4) */}
          {currentMoveInGraph && (
            <ReferenceLine
              x={currentMove}
              stroke="#1976d2"
              strokeDasharray="4 3"
              strokeWidth={2}
              data-testid="current-move-indicator"
            />
          )}

          <Line
            type="monotone"
            dataKey="clampedEval"
            stroke="#1976d2"
            strokeWidth={2}
            dot={<CustomDot />}
            activeDot={{ r: 5, fill: "#0d47a1" }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
