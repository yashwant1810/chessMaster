import type { PlayerAnalysisSummary } from "../types";
import "./GameSummary.css";

export interface GameSummaryProps {
  whiteSummary: PlayerAnalysisSummary | null;
  blackSummary: PlayerAnalysisSummary | null;
  whitePlayer: string;
  blackPlayer: string;
}

const ROWS: { key: string; label: string; color: string }[] = [
  { key: "best_count", label: "Best", color: "#56b556" },
  { key: "excellent_count", label: "Excellent", color: "#56b556" },
  { key: "good_count", label: "Good", color: "#5b9bd5" },
  { key: "inaccuracy_count", label: "Inaccuracy", color: "#f5c542" },
  { key: "mistake_count", label: "Mistake", color: "#e8833a" },
  { key: "blunder_count", label: "Blunder", color: "#e05252" },
];

function getCount(summary: PlayerAnalysisSummary, key: string): number {
  return (summary as unknown as Record<string, number>)[key] ?? 0;
}

export default function GameSummary({ whiteSummary, blackSummary, whitePlayer, blackPlayer }: GameSummaryProps) {
  if (!whiteSummary || !blackSummary) {
    return <div className="gs"><p className="gs__empty">Performance data requires completed analysis.</p></div>;
  }

  return (
    <div className="gs">
      <h3>Game Summary</h3>
      <table className="gs__table">
        <thead>
          <tr>
            <th className="gs__th-player">{whitePlayer}</th>
            <th className="gs__th-label"></th>
            <th className="gs__th-player">{blackPlayer}</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ key, label, color }) => (
            <tr key={key}>
              <td className="gs__count">{getCount(whiteSummary, key)}</td>
              <td className="gs__label">
                <span className="gs__dot" style={{ background: color }} />
                {label}
              </td>
              <td className="gs__count">{getCount(blackSummary, key)}</td>
            </tr>
          ))}
          <tr className="gs__rating-row">
            <td className="gs__rating">{whiteSummary.final_performance_rating}</td>
            <td className="gs__label">Performance Rating</td>
            <td className="gs__rating">{blackSummary.final_performance_rating}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
