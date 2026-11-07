import { useParams } from "react-router-dom";
import AnalysisView from "../components/AnalysisView";

/**
 * Analysis page — displays move-by-move analysis for a game.
 * Extracts `gameId` from the URL and delegates to AnalysisView.
 */
export default function AnalysisPage() {
  const { gameId } = useParams<{ gameId: string }>();

  if (!gameId) {
    return (
      <div data-testid="analysis-page">
        <h2>Game Analysis</h2>
        <p data-testid="no-game-id">No game ID provided.</p>
      </div>
    );
  }

  return (
    <div data-testid="analysis-page">
      <AnalysisView gameId={gameId} />
    </div>
  );
}
