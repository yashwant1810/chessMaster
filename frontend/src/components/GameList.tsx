import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { GameSummary, SortField, SortOrder } from "../types";
import { sortGames } from "../utils/sortGames";
import GameListItem from "./GameListItem";
import "./GameList.css";

export interface GameListProps {
  games: GameSummary[];
}

const SORT_OPTIONS: { field: SortField; label: string }[] = [
  { field: "date", label: "Date" },
  { field: "result", label: "Result" },
  { field: "time_control", label: "Time" },
];

export default function GameList({ games }: GameListProps) {
  const navigate = useNavigate();
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const sorted = useMemo(() => sortGames(games, sortField, sortOrder), [games, sortField, sortOrder]);

  const handleSelect = useCallback((gameId: string) => navigate(`/analysis/${gameId}`), [navigate]);

  const toggleSort = useCallback((field: SortField) => {
    if (field === sortField) {
      setSortOrder((o) => (o === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  }, [sortField]);

  if (games.length === 0) {
    return <div className="game-list-empty">No games available.</div>;
  }

  return (
    <div className="game-list" data-testid="game-list">
      <div className="game-list__controls">
        <span className="game-list__label">Sort by</span>
        {SORT_OPTIONS.map((opt) => (
          <button
            key={opt.field}
            className={`game-list__sort-btn ${sortField === opt.field ? "game-list__sort-btn--active" : ""}`}
            onClick={() => toggleSort(opt.field)}
          >
            {opt.label} {sortField === opt.field ? (sortOrder === "desc" ? "↓" : "↑") : ""}
          </button>
        ))}
      </div>
      <div className="game-list__items">
        {sorted.map((game) => (
          <GameListItem key={game.game_id} game={game} onSelect={handleSelect} />
        ))}
      </div>
    </div>
  );
}
