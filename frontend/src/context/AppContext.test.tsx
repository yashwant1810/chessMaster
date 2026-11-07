import { render, screen, act } from "@testing-library/react";
import { AppProvider, useAppContext } from "./AppContext";

/** Test component that exposes context values for assertions. */
function ContextConsumer() {
  const { username, games, setUsername, setGames } = useAppContext();

  return (
    <div>
      <span data-testid="username">{username}</span>
      <span data-testid="games-count">{games.length}</span>
      <button
        data-testid="set-username"
        onClick={() => setUsername("hikaru")}
      />
      <button
        data-testid="set-games"
        onClick={() =>
          setGames([
            {
              game_id: "g1",
              date_played: "2024-01-01T00:00:00Z",
              opponent: "magnus",
              result: "win",
              time_control: "600",
              opening_name: "Sicilian",
              is_analyzed: false,
            },
          ])
        }
      />
    </div>
  );
}

describe("AppContext", () => {
  it("provides default empty state", () => {
    render(
      <AppProvider>
        <ContextConsumer />
      </AppProvider>,
    );

    expect(screen.getByTestId("username").textContent).toBe("");
    expect(screen.getByTestId("games-count").textContent).toBe("0");
  });

  it("allows updating the username", () => {
    render(
      <AppProvider>
        <ContextConsumer />
      </AppProvider>,
    );

    act(() => {
      screen.getByTestId("set-username").click();
    });

    expect(screen.getByTestId("username").textContent).toBe("hikaru");
  });

  it("allows updating the games list", () => {
    render(
      <AppProvider>
        <ContextConsumer />
      </AppProvider>,
    );

    act(() => {
      screen.getByTestId("set-games").click();
    });

    expect(screen.getByTestId("games-count").textContent).toBe("1");
  });

  it("throws when used outside AppProvider", () => {
    // Suppress the expected error log from React
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => render(<ContextConsumer />)).toThrow(
      "useAppContext must be used within an AppProvider",
    );

    spy.mockRestore();
  });
});
