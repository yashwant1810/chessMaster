import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { GameSummary } from "../types";

/** Shape of the global application state. */
export interface AppState {
  /** The chess.com username whose games are currently loaded. */
  username: string;
  /** The list of fetched games for the current username. */
  games: GameSummary[];
  /** Update the current username. */
  setUsername: (username: string) => void;
  /** Replace the entire games list (e.g. after a fetch). */
  setGames: (games: GameSummary[]) => void;
}

const AppContext = createContext<AppState | undefined>(undefined);

/** Provider that wraps the app and exposes global state. */
export function AppProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState("");
  const [games, setGames] = useState<GameSummary[]>([]);

  const setUsernameStable = useCallback(
    (value: string) => setUsername(value),
    [],
  );
  const setGamesStable = useCallback(
    (value: GameSummary[]) => setGames(value),
    [],
  );

  const value = useMemo<AppState>(
    () => ({ username, games, setUsername: setUsernameStable, setGames: setGamesStable }),
    [username, games, setUsernameStable, setGamesStable],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

/** Hook to consume global app state. Throws if used outside AppProvider. */
export function useAppContext(): AppState {
  const ctx = useContext(AppContext);
  if (ctx === undefined) {
    throw new Error("useAppContext must be used within an AppProvider");
  }
  return ctx;
}
