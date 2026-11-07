import { Route, Routes, Link } from "react-router-dom";
import HomePage from "./pages/HomePage";
import AnalysisPage from "./pages/AnalysisPage";
import "./App.css";

function App() {
  return (
    <div className="app-layout">
      <header className="app-header">
        <Link to="/" className="app-title-link">
          <h1 className="app-title">♟ Chess Review Engine</h1>
        </Link>
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/analysis/:gameId" element={<AnalysisPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
