import { useParams } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import AnalysisView from "../components/AnalysisView";

export default function AnalysisPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const { username } = useAppContext();

  if (!gameId) return <p style={{ color: "#ccc", padding: "2rem" }}>No game selected.</p>;
  return <AnalysisView gameId={gameId} username={username} />;
}
