import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import App from "./App";

function renderApp(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <AppProvider>
        <App />
      </AppProvider>
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("renders the header with app title", () => {
    renderApp();
    expect(
      screen.getByRole("heading", { name: /chess review engine/i }),
    ).toBeInTheDocument();
  });

  it("renders the home page at /", () => {
    renderApp("/");
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
  });

  it("renders the analysis page at /analysis/:gameId", () => {
    renderApp("/analysis/abc-123");
    expect(screen.getByTestId("analysis-page")).toBeInTheDocument();
    // AnalysisView now renders (shows loading initially)
    expect(screen.getByTestId("analysis-view")).toBeInTheDocument();
  });

  it("renders home page by default (no analysis page visible)", () => {
    renderApp("/");
    expect(screen.getByTestId("home-page")).toBeInTheDocument();
    expect(screen.queryByTestId("analysis-page")).not.toBeInTheDocument();
  });
});
