import ProfileInput from "../components/ProfileInput";
import GameList from "../components/GameList";
import { useAppContext } from "../context/AppContext";

export default function HomePage() {
  const { games, username } = useAppContext();

  return (
    <div data-testid="home-page" style={{ maxWidth: 900, margin: "0 auto" }}>
      <h2 style={{ fontSize: "1.8rem", fontWeight: 700, marginBottom: 4 }}>Game Analysis</h2>
      <p style={{ color: "#888", marginBottom: 20, fontSize: "0.95rem" }}>
        Pull your latest games and review any one move-by-move with Stockfish.
      </p>
      <div style={{ background: "#2b2926", borderRadius: 10, padding: "20px 24px", marginBottom: 24 }}>
        <ProfileInput />
      </div>
      {games.length > 0 && (
        <div style={{ background: "#2b2926", borderRadius: 10, padding: "20px 24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: 600 }}>
              {username ? `${username}'s Games` : "Your Games"}
            </h3>
            <span style={{ color: "#888", fontSize: "0.85rem" }}>
              Click any game for a full Stockfish review
            </span>
          </div>
          <GameList games={games} />
        </div>
      )}
    </div>
  );
}
