import "./EvaluationBar.css";

/** Maximum centipawn magnitude shown on the bar. */
const MAX_CP = 2000;

export interface EvaluationBarProps {
  /** Centipawn evaluation from White's perspective. Positive = White advantage. */
  evaluation: number | null;
  /** Mate-in-N indicator. Positive = White mates, negative = Black mates. */
  mateIn: number | null;
  /** Height of the bar in pixels. Should match the board height. */
  height?: number;
}

/**
 * Computes the percentage of the bar that should be white (from 0–100).
 *
 * - evaluation = 0  → 50 % (even position)
 * - evaluation > 0  → > 50 % (White advantage)
 * - evaluation < 0  → < 50 % (Black advantage)
 * - mateIn positive → 100 % (White mates)
 * - mateIn negative → 0 %   (Black mates)
 * - Clamped at ±MAX_CP before mapping to percentage.
 */
export function computeWhitePercent(
  evaluation: number | null,
  mateIn: number | null,
): number {
  // Checkmate: full bar for winning side
  if (mateIn !== null && mateIn !== undefined) {
    return mateIn > 0 ? 100 : 0;
  }

  // No evaluation data → show neutral position
  if (evaluation === null || evaluation === undefined) {
    return 50;
  }

  // Clamp to ±MAX_CP
  const clamped = Math.max(-MAX_CP, Math.min(MAX_CP, evaluation));

  // Map [-MAX_CP, +MAX_CP] → [0, 100]
  return ((clamped + MAX_CP) / (2 * MAX_CP)) * 100;
}

/**
 * Formats the evaluation for display as text on the bar.
 */
export function formatEvaluation(
  evaluation: number | null,
  mateIn: number | null,
): string {
  if (mateIn !== null && mateIn !== undefined) {
    const absM = Math.abs(mateIn);
    return `M${absM}`;
  }

  if (evaluation === null || evaluation === undefined) {
    return "–";
  }

  const pawnValue = Math.abs(evaluation) / 100;
  const sign = evaluation >= 0 ? "+" : "-";
  return `${sign}${pawnValue.toFixed(1)}`;
}

/**
 * EvaluationBar — a vertical bar adjacent to the chess board showing
 * the current position's advantage in centipawns.
 *
 * - Positive values (White advantage) extend the white section upward from the bottom.
 * - Negative values (Black advantage) extend the black section downward from the top.
 * - Checkmate positions show full bar for the winning side.
 * - Capped at ±2000 centipawns for display purposes.
 *
 * @see Requirements 10.5, 10.6
 */
export default function EvaluationBar({
  evaluation,
  mateIn,
  height = 560,
}: EvaluationBarProps) {
  const whitePercent = computeWhitePercent(evaluation, mateIn);
  const label = formatEvaluation(evaluation, mateIn);

  // Determine which side has the advantage for label placement
  const isWhiteAdvantage = whitePercent >= 50;

  return (
    <div
      className="eval-bar"
      style={{ height }}
      data-testid="evaluation-bar"
      role="meter"
      aria-label={`Position evaluation: ${label}`}
      aria-valuenow={evaluation ?? 0}
      aria-valuemin={-MAX_CP}
      aria-valuemax={MAX_CP}
    >
      {/* Black section (top) */}
      <div
        className="eval-bar__black"
        style={{ height: `${100 - whitePercent}%` }}
        data-testid="eval-bar-black"
      >
        {!isWhiteAdvantage && (
          <span className="eval-bar__label eval-bar__label--black">
            {label}
          </span>
        )}
      </div>

      {/* White section (bottom) */}
      <div
        className="eval-bar__white"
        style={{ height: `${whitePercent}%` }}
        data-testid="eval-bar-white"
      >
        {isWhiteAdvantage && (
          <span className="eval-bar__label eval-bar__label--white">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}
