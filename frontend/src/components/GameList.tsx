import { useState, useMemo, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { GameSummary, SortField, SortOrder } from "../types";
import { sortGames } from "../utils/sortGames";
import GameListItem from "./GameListItem";
import "./GameList.css";

export interface GameListProps {
  games: GameSummary[];
}

const SORT_FIELDS: { field: SortField; label: string }[] = [
  { field: "date", label: "Date" },
  { field: "result", label: "Result" },
  { field: "time_control", label: "Time Control" },
];

/**
 * Scrollable, sortable list of fetched games.
 *
 * Default sort: date descending (most recent first).
 * Navigates to /analysis/:gameId on row click.
 * Displays "no games available" when the list is empty.
 */
export default function GameList({ games }: GameListProps) {
  const navigate = useNavigate();
  const [sortField, setSortField] = useState<SortField>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const sortedGames = useMemo(
    () => sortGames(games, sortField, sortOrder),
    [games, sortField, sortOrder],
  );

  const handleSelect = useCallback(
    (gameId: string) => {
      navigate(`/analysis/${gameId}`);
    },
    [navigate],
  );

  const toggleSort = useCallback(
    (field: SortField) => {
      if (field === sortField) {
        setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        setSortField(field);
        setSortOrder(field === "date" ? "desc" : "asc");
      }
    },
    [sortField],
  );

  if (games.length === 0) {
    return (
      <div className="game-list-empty" data-testid="game-list-empty">
        <p>No games available.</p>
      </div>
    );
  }

  return (
    <div className="game-list-container" data-testid="game-list">
      <div className="game-list-sort-controls" role="toolbar" aria-label="Sort controls">
        {SORT_FIELDS.map(({ field, label }) => {
          const isActive = field === sortField;
          return (
            <button
              key={field}
              className={`sort-button ${isActive ? "sort-active" : ""}`}
              onClick={() => toggleSort(field)}
              aria-pressed={isActive}
              aria-label={`Sort by ${label} ${isActive ? (sortOrder === "asc" ? "ascending" : "descending") : ""}`}
            >
              {label}
              {isActive && (
                <span className="sort-indicator" aria-hidden="true">
                  {sortOrder === "asc" ? " ↑" : " ↓"}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="game-list-scroll">
        <table className="game-list-table" role="grid">
          <thead>
            <tr>
              <th className="game-header">Date</th>
              <th className="game-header">Opponent</th>
              <th className="game-header">Result</th>
              <th className="game-header">Time Control</th>
              <th className="game-header">Opening</th>
            </tr>
          </thead>
          <tbody>
            {sortedGames.map((game) => (
              <GameListItem
                key={game.game_id}
                game={game}
                onSelect={handleSelect}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
