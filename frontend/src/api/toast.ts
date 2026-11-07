/**
 * Simple toast notification system for displaying error messages.
 *
 * Creates DOM-based toast notifications that auto-dismiss after a timeout.
 * Used by the API client to surface network and timeout errors to users.
 */

const TOAST_CONTAINER_ID = "chess-review-toast-container";
const DEFAULT_DURATION_MS = 5000;

/** Ensures the toast container exists in the DOM. */
function getOrCreateContainer(): HTMLElement {
  let container = document.getElementById(TOAST_CONTAINER_ID);
  if (!container) {
    container = document.createElement("div");
    container.id = TOAST_CONTAINER_ID;
    container.setAttribute("role", "status");
    container.setAttribute("aria-live", "polite");
    Object.assign(container.style, {
      position: "fixed",
      top: "16px",
      right: "16px",
      zIndex: "9999",
      display: "flex",
      flexDirection: "column",
      gap: "8px",
      pointerEvents: "none",
    });
    document.body.appendChild(container);
  }
  return container;
}

/** Removes a toast element with a fade-out animation. */
function dismissToast(toast: HTMLElement): void {
  toast.style.opacity = "0";
  toast.style.transform = "translateX(100%)";
  setTimeout(() => toast.remove(), 300);
}

/**
 * Show a toast notification.
 *
 * @param message - The error message to display.
 * @param duration - Auto-dismiss duration in ms (default 5000).
 */
export function showToast(
  message: string,
  duration: number = DEFAULT_DURATION_MS,
): void {
  const container = getOrCreateContainer();

  const toast = document.createElement("div");
  toast.setAttribute("role", "alert");
  Object.assign(toast.style, {
    background: "#dc2626",
    color: "#fff",
    padding: "12px 20px",
    borderRadius: "8px",
    fontSize: "14px",
    lineHeight: "1.4",
    maxWidth: "380px",
    boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
    pointerEvents: "auto",
    cursor: "pointer",
    transition: "opacity 0.3s ease, transform 0.3s ease",
    opacity: "0",
    transform: "translateX(100%)",
  });
  toast.textContent = message;

  toast.addEventListener("click", () => dismissToast(toast));
  container.appendChild(toast);

  // Trigger enter animation on next frame
  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateX(0)";
  });

  setTimeout(() => dismissToast(toast), duration);
}
