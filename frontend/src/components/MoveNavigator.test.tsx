import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MoveNavigator from "./MoveNavigator";

describe("MoveNavigator", () => {
  // ---- Button rendering ------------------------------------------------

  it("renders all four navigation buttons", () => {
    render(
      <MoveNavigator currentMove={5} totalMoves={20} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "First move" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous move" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next move" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Last move" })).toBeInTheDocument();
  });

  it("renders inside a navigation landmark", () => {
    render(
      <MoveNavigator currentMove={0} totalMoves={10} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("navigation", { name: "Move navigation" })).toBeInTheDocument();
  });

  // ---- Button click handlers -------------------------------------------

  it("calls onNavigate(0) when first-move button is clicked", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={10} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "First move" }));
    expect(onNavigate).toHaveBeenCalledWith(0);
  });

  it("calls onNavigate(currentMove - 1) when previous-move button is clicked", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={7} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "Previous move" }));
    expect(onNavigate).toHaveBeenCalledWith(6);
  });

  it("calls onNavigate(currentMove + 1) when next-move button is clicked", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={7} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "Next move" }));
    expect(onNavigate).toHaveBeenCalledWith(8);
  });

  it("calls onNavigate(totalMoves) when last-move button is clicked", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={7} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "Last move" }));
    expect(onNavigate).toHaveBeenCalledWith(20);
  });

  // ---- Disabled state at initial position (Requirement 10.7) -----------

  it("disables first and previous buttons at initial position (move 0)", () => {
    render(
      <MoveNavigator currentMove={0} totalMoves={20} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "First move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Last move" })).toBeEnabled();
  });

  it("does not call onNavigate when clicking disabled first button at initial position", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={0} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "First move" }));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  // ---- Disabled state at final position (Requirement 10.8) -------------

  it("disables next and last buttons at final position", () => {
    render(
      <MoveNavigator currentMove={20} totalMoves={20} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "First move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Previous move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Last move" })).toBeDisabled();
  });

  it("does not call onNavigate when clicking disabled next button at final position", async () => {
    const onNavigate = vi.fn();
    const user = userEvent.setup();

    render(
      <MoveNavigator currentMove={20} totalMoves={20} onNavigate={onNavigate} />,
    );

    await user.click(screen.getByRole("button", { name: "Next move" }));
    expect(onNavigate).not.toHaveBeenCalled();
  });

  // ---- All buttons disabled when totalMoves is 0 -----------------------

  it("disables all buttons when there are no moves (totalMoves = 0)", () => {
    render(
      <MoveNavigator currentMove={0} totalMoves={0} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "First move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Previous move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next move" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Last move" })).toBeDisabled();
  });

  // ---- Keyboard navigation (Requirement 10.4) --------------------------

  describe("keyboard navigation", () => {
    it("navigates to previous move on left arrow key press", () => {
      const onNavigate = vi.fn();

      render(
        <MoveNavigator currentMove={5} totalMoves={20} onNavigate={onNavigate} />,
      );

      fireEvent.keyDown(document, { key: "ArrowLeft" });
      expect(onNavigate).toHaveBeenCalledWith(4);
    });

    it("navigates to next move on right arrow key press", () => {
      const onNavigate = vi.fn();

      render(
        <MoveNavigator currentMove={5} totalMoves={20} onNavigate={onNavigate} />,
      );

      fireEvent.keyDown(document, { key: "ArrowRight" });
      expect(onNavigate).toHaveBeenCalledWith(6);
    });

    it("does not navigate before initial position on left arrow", () => {
      const onNavigate = vi.fn();

      render(
        <MoveNavigator currentMove={0} totalMoves={20} onNavigate={onNavigate} />,
      );

      fireEvent.keyDown(document, { key: "ArrowLeft" });
      expect(onNavigate).not.toHaveBeenCalled();
    });

    it("does not navigate past final position on right arrow", () => {
      const onNavigate = vi.fn();

      render(
        <MoveNavigator currentMove={20} totalMoves={20} onNavigate={onNavigate} />,
      );

      fireEvent.keyDown(document, { key: "ArrowRight" });
      expect(onNavigate).not.toHaveBeenCalled();
    });

    it("ignores non-arrow key presses", () => {
      const onNavigate = vi.fn();

      render(
        <MoveNavigator currentMove={5} totalMoves={20} onNavigate={onNavigate} />,
      );

      fireEvent.keyDown(document, { key: "Enter" });
      fireEvent.keyDown(document, { key: "Space" });
      fireEvent.keyDown(document, { key: "ArrowUp" });
      fireEvent.keyDown(document, { key: "ArrowDown" });
      expect(onNavigate).not.toHaveBeenCalled();
    });

    it("cleans up keyboard listener on unmount", () => {
      const onNavigate = vi.fn();

      const { unmount } = render(
        <MoveNavigator currentMove={5} totalMoves={20} onNavigate={onNavigate} />,
      );

      unmount();

      fireEvent.keyDown(document, { key: "ArrowLeft" });
      fireEvent.keyDown(document, { key: "ArrowRight" });
      expect(onNavigate).not.toHaveBeenCalled();
    });
  });

  // ---- Mid-game: all buttons enabled -----------------------------------

  it("enables all buttons at a mid-game position", () => {
    render(
      <MoveNavigator currentMove={10} totalMoves={20} onNavigate={() => {}} />,
    );

    expect(screen.getByRole("button", { name: "First move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Previous move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next move" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Last move" })).toBeEnabled();
  });
});
