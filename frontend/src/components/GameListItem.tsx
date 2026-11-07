import type { GameSummary } from "../types";
import "./GameListItem.css";

export interface GameListItemProps {
  game: GameSummary;
  onSelect: (gameId: string) => void;
}

const RESULT_LABELS: Record<string, string> = {
  win: "Win",
  loss: "Loss",
  draw: "Draw",
};

function resultClassName(result: string): string {
  switch (result) {
    case "win":
      return "result-win";
    case "loss":
      return "result-loss";
    case "draw":
      return "result-draw";
    default:
      return "";
  }
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * Renders a single row in the game list.
 *
 * Shows date, opponent, result, time control, and opening name.
 * Displays "unavailable" for any null/missing metadata field.
 */
export default function GameListItem({ game, onSelect }: GameListItemProps) {
  return (
    <tr
      className="game-list-item"
      data-testid={`game-item-${game.game_id}`}
      onClick={() => onSelect(game.game_id)}
      role="row"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(game.game_id);
        }
      }}
    >
      <td className="game-cell game-date">{formatDate(game.date_played)}</td>
      <td className="game-cell game-opponent">{game.opponent}</td>
      <td className={`game-cell game-result ${resultClassName(game.result)}`}>
        {RESULT_LABELS[game.result] ?? game.result}
      </td>
      <td className="game-cell game-time-control">
        {game.time_control ?? (
          <span className="unavailable">unavailable</span>
        )}
      </td>
      <td className="game-cell game-opening">
        {game.opening_name ?? (
          <span className="unavailable">unavailable</span>
        )}
      </td>
    </tr>
  );
}
