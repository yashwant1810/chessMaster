import type { PlayerAnalysisSummary, MoveClassification } from "../types";
import "./GameSummary.css";

export interface GameSummaryProps {
  whiteSummary: PlayerAnalysisSummary | null;
  blackSummary: PlayerAnalysisSummary | null;
  whitePlayer: string;
  blackPlayer: string;
}

/**
 * Classification → icon + CSS class mapping.
 *
 * Uses the same color-coded icons as MoveList:
 *   best       = green ★
 *   excellent  = dark-green ◆
 *   good       = blue ●
 *   inaccuracy = yellow ▲
 *   mistake    = orange ■
 *   blunder    = red ✖
 */
const CLASSIFICATION_CONFIG: {
  key: keyof Pick<
    PlayerAnalysisSummary,
    | "best_count"
    | "excellent_count"
    | "good_count"
    | "inaccuracy_count"
    | "mistake_count"
    | "blunder_count"
  >;
  label: string;
  classification: MoveClassification;
  icon: string;
  cssClass: string;
}[] = [
  {
    key: "best_count",
    label: "Best",
    classification: "best",
    icon: "★",
    cssClass: "classification-icon--best",
  },
  {
    key: "excellent_count",
    label: "Excellent",
    classification: "excellent",
    icon: "◆",
    cssClass: "classification-icon--excellent",
  },
  {
    key: "good_count",
    label: "Good",
    classification: "good",
    icon: "●",
    cssClass: "classification-icon--good",
  },
  {
    key: "inaccuracy_count",
    label: "Inaccuracy",
    classification: "inaccuracy",
    icon: "▲",
    cssClass: "classification-icon--inaccuracy",
  },
  {
    key: "mistake_count",
    label: "Mistake",
    classification: "mistake",
    icon: "■",
    cssClass: "classification-icon--mistake",
  },
  {
    key: "blunder_count",
    label: "Blunder",
    classification: "blunder",
    icon: "✖",
    cssClass: "classification-icon--blunder",
  },
];

/**
 * Renders one player's classification counts and performance rating.
 */
function PlayerSummary({
  summary,
  playerName,
}: {
  summary: PlayerAnalysisSummary;
  playerName: string;
}) {
  return (
    <div className="game-summary-player" data-testid={`player-summary-${playerName}`}>
      <h4 className="game-summary-player-name">{playerName}</h4>

      <ul className="game-summary-classifications" aria-label={`${playerName} move classifications`}>
        {CLASSIFICATION_CONFIG.map((cfg) => (
          <li key={cfg.classification} className="game-summary-classification-row">
            <span
              className={`classification-icon ${cfg.cssClass}`}
              aria-hidden="true"
            >
              {cfg.icon}
            </span>
            <span className="game-summary-classification-label">{cfg.label}</span>
            <span
              className="game-summary-classification-count"
              data-testid={`${playerName}-${cfg.classification}-count`}
            >
              {summary[cfg.key]}
            </span>
          </li>
        ))}
      </ul>

      <div className="game-summary-rating" data-testid={`${playerName}-performance-rating`}>
        <span className="game-summary-rating-label">Performance Rating</span>
        <span className="game-summary-rating-value">
          {summary.final_performance_rating}
        </span>
      </div>
    </div>
  );
}

/**
 * Game summary component displaying classification counts and performance
 * ratings for both players.
 *
 * Shows a message when analysis data is not yet available
 * (Requirement 8.4).
 *
 * Requirements: 6.4, 8.3, 8.4
 */
export default function GameSummary({
  whiteSummary,
  blackSummary,
  whitePlayer,
  blackPlayer,
}: GameSummaryProps) {
  const hasData = whiteSummary !== null && blackSummary !== null;

  if (!hasData) {
    return (
      <div className="game-summary" data-testid="game-summary">
        <h3 className="game-summary-title">Game Summary</h3>
        <p
          className="game-summary-unavailable"
          data-testid="game-summary-unavailable"
        >
          Performance data requires completed analysis
        </p>
      </div>
    );
  }

  return (
    <div className="game-summary" data-testid="game-summary">
      <h3 className="game-summary-title">Game Summary</h3>
      <div className="game-summary-players">
        <PlayerSummary summary={whiteSummary} playerName={whitePlayer} />
        <PlayerSummary summary={blackSummary} playerName={blackPlayer} />
      </div>
    </div>
  );
}
