"use client";

// Minimal toast. Portal to #modal-root so it isn't clipped by
// AppShell overflow contexts. One visible at a time, owned by the
// caller (no queue, no notification service); 2-second auto-dismiss
// cleared if the caller unmounts / closes us early.
//
// See phase-3 plan D14.

import { useEffect, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";

interface ToastProps {
  open: boolean;
  message: ReactNode;
  hint?: ReactNode;
  onDismiss: () => void;
  /**
   * Auto-dismiss delay in ms. Lowerable for tests; default 2000.
   */
  durationMs?: number;
}

export function Toast({
  open,
  message,
  hint,
  onDismiss,
  durationMs = 2000,
}: ToastProps) {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  useEffect(() => {
    setTarget(document.getElementById("modal-root"));
  }, []);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(onDismiss, durationMs);
    return () => window.clearTimeout(id);
  }, [open, durationMs, onDismiss]);

  if (!open || !target) return null;

  return createPortal(
    <div
      data-testid="toast"
      role="status"
      aria-live="polite"
      className={clsx(
        "fixed bottom-24 right-24 z-30 flex items-center gap-10",
        "rounded-4 border border-line bg-panel px-14 py-10 font-mono text-11 text-text",
        "shadow-modal",
      )}
    >
      <span>{message}</span>
      {hint != null && (
        <kbd className="rounded-3 border border-line bg-panel2 px-5 py-1 font-mono text-10 text-text-dim">
          {hint}
        </kbd>
      )}
    </div>,
    target,
  );
}
