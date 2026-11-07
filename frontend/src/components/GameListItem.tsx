import type { GameSummary } from "../types";
import "./GameListItem.css";

export interface GameListItemProps {
  game: GameSummary;
  onSelect: (gameId: string) => void;
}

const RESULT_LABELS: Record<string, string> = { win: "Win", loss: "Loss", draw: "Draw" };

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "Just now";
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch { return iso; }
}

function timeControlLabel(tc: string | null): string {
  if (!tc) return "—";
  const secs = parseInt(tc, 10);
  if (isNaN(secs)) return tc;
  if (secs < 180) return "⚡ Bullet";
  if (secs < 600) return "🔥 Blitz";
  if (secs <= 1800) return "⏱ Rapid";
  return "📅 Daily";
}

function timeControlShort(tc: string | null): string {
  if (!tc) return "";
  const secs = parseInt(tc, 10);
  if (isNaN(secs)) return tc;
  return `${Math.floor(secs / 60)} min`;
}

export default function GameListItem({ game, onSelect }: GameListItemProps) {
  const barClass = game.result === "win" ? "bar--win" : game.result === "loss" ? "bar--loss" : "bar--draw";

  return (
    <div
      className="game-card"
      data-testid={`game-item-${game.game_id}`}
      onClick={() => onSelect(game.game_id)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(game.game_id); } }}
      role="row"
      tabIndex={0}
    >
      <div className={`game-card__bar ${barClass}`} />
      <div className="game-card__info">
        <div className="game-card__opponent">
          {game.opponent} <span className="game-card__result">{RESULT_LABELS[game.result] ?? game.result}</span>
        </div>
        <div className="game-card__meta">
          <span className="game-card__tc">{timeControlLabel(game.time_control)}</span>
          <span className="game-card__time">{timeControlShort(game.time_control)}</span>
          <span className="game-card__sep">·</span>
          <span className="game-card__date">{formatDate(game.date_played)}</span>
        </div>
      </div>
      <div className="game-card__opening">
        {game.opening_name ? game.opening_name.split("/").pop()?.replace(/-/g, " ") : <span className="unavailable">—</span>}
      </div>
      <div className="game-card__action">
        {game.is_analyzed
          ? <span className="game-card__analyzed">✓ Analyzed</span>
          : <span className="game-card__analyze-btn">Analyze →</span>}
      </div>
    </div>
  );
}
