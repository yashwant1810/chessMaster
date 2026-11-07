import "./ProgressIndicator.css";

export interface ProgressIndicatorProps {
  /** Progress percentage (0–100). Used for analysis type. */
  progress: number;
  /** Display mode: 'analysis' shows a progress bar; 'fetch' shows an activity indicator. */
  type: "fetch" | "analysis";
}

/**
 * ProgressIndicator — displays analysis progress (bar + %) or fetch activity (animated dots).
 *
 * Requirements: 1.9, 5.5, 5.6
 */
export default function ProgressIndicator({
  progress,
  type,
}: ProgressIndicatorProps) {
  const clampedProgress = Math.min(100, Math.max(0, Math.round(progress)));

  if (type === "analysis") {
    return (
      <div className="progress-indicator progress-indicator--analysis">
        <div
          className="progress-bar"
          role="progressbar"
          aria-valuenow={clampedProgress}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Analysis progress: ${clampedProgress}%`}
        >
          <div
            className="progress-bar__fill"
            style={{ width: `${clampedProgress}%` }}
          />
        </div>
        <span className="progress-indicator__text">
          Analyzing… {clampedProgress}%
        </span>
      </div>
    );
  }

  // type === "fetch"
  return (
    <div
      className="progress-indicator progress-indicator--fetch"
      role="status"
      aria-label="Fetching games"
    >
      <span className="progress-indicator__dots" aria-hidden="true">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
      </span>
      <span className="progress-indicator__text">Fetching games…</span>
    </div>
  );
}
