import { render, screen } from "@testing-library/react";
import ProgressIndicator from "./ProgressIndicator";

describe("ProgressIndicator", () => {
  // ---- Analysis type ------------------------------------------------

  describe('type="analysis"', () => {
    it("renders a progress bar with the correct percentage", () => {
      render(<ProgressIndicator progress={45} type="analysis" />);

      const bar = screen.getByRole("progressbar");
      expect(bar).toBeInTheDocument();
      expect(bar).toHaveAttribute("aria-valuenow", "45");
      expect(bar).toHaveAttribute("aria-valuemin", "0");
      expect(bar).toHaveAttribute("aria-valuemax", "100");
      expect(screen.getByText("Analyzing… 45%")).toBeInTheDocument();
    });

    it("renders a fill element with the correct width", () => {
      const { container } = render(
        <ProgressIndicator progress={72} type="analysis" />,
      );

      const fill = container.querySelector(".progress-bar__fill");
      expect(fill).toHaveStyle({ width: "72%" });
    });

    it("clamps progress to 0 when negative", () => {
      render(<ProgressIndicator progress={-10} type="analysis" />);

      const bar = screen.getByRole("progressbar");
      expect(bar).toHaveAttribute("aria-valuenow", "0");
      expect(screen.getByText("Analyzing… 0%")).toBeInTheDocument();
    });

    it("clamps progress to 100 when exceeding 100", () => {
      render(<ProgressIndicator progress={150} type="analysis" />);

      const bar = screen.getByRole("progressbar");
      expect(bar).toHaveAttribute("aria-valuenow", "100");
      expect(screen.getByText("Analyzing… 100%")).toBeInTheDocument();
    });

    it("rounds fractional progress to nearest integer", () => {
      render(<ProgressIndicator progress={33.7} type="analysis" />);

      const bar = screen.getByRole("progressbar");
      expect(bar).toHaveAttribute("aria-valuenow", "34");
      expect(screen.getByText("Analyzing… 34%")).toBeInTheDocument();
    });

    it("has an accessible label describing the progress", () => {
      render(<ProgressIndicator progress={60} type="analysis" />);

      const bar = screen.getByRole("progressbar");
      expect(bar).toHaveAttribute(
        "aria-label",
        "Analysis progress: 60%",
      );
    });
  });

  // ---- Fetch type ---------------------------------------------------

  describe('type="fetch"', () => {
    it("renders an activity indicator with status text", () => {
      render(<ProgressIndicator progress={0} type="fetch" />);

      expect(screen.getByText("Fetching games…")).toBeInTheDocument();
    });

    it("has role=status for screen readers", () => {
      render(<ProgressIndicator progress={0} type="fetch" />);

      const status = screen.getByRole("status");
      expect(status).toBeInTheDocument();
      expect(status).toHaveAttribute("aria-label", "Fetching games");
    });

    it("renders three animated dots", () => {
      const { container } = render(
        <ProgressIndicator progress={0} type="fetch" />,
      );

      const dots = container.querySelectorAll(".dot");
      expect(dots).toHaveLength(3);
    });

    it("hides the dots from assistive technology", () => {
      const { container } = render(
        <ProgressIndicator progress={0} type="fetch" />,
      );

      const dotsWrapper = container.querySelector(
        ".progress-indicator__dots",
      );
      expect(dotsWrapper).toHaveAttribute("aria-hidden", "true");
    });

    it("does not render a progress bar", () => {
      render(<ProgressIndicator progress={0} type="fetch" />);

      expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
    });
  });
});
