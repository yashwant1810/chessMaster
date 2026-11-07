/**
 * Home page — profile input and game list.
 */
import ProfileInput from "../components/ProfileInput";
import GameList from "../components/GameList";
import { useAppContext } from "../context/AppContext";

export default function HomePage() {
  const { games, username } = useAppContext();

  return (
    <div data-testid="home-page">
      <h2>Welcome</h2>
      <p>Enter your chess.com username or game URL to load your games.</p>
      <ProfileInput />
      {games.length > 0 && (
        <section>
          <h3>{username ? `${username}'s Games` : "Games"} ({games.length})</h3>
          <GameList games={games} />
        </section>
      )}
    </div>
  );
}
