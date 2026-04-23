"use client";

// Shared modal: portal into #modal-root, backdrop, Escape close,
// autofocus the first focusable child, restore focus on close, and a
// Tab/Shift-Tab focus trap inlined at the bottom. Consumers own the
// width via `className` (no widthPx prop).
//
// See phase-3 plan D1.

import {
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  label: string;
  children: ReactNode;
  className?: string;
  dismissOnBackdrop?: boolean;
}

export function Modal({
  open,
  onClose,
  label,
  children,
  className,
  dismissOnBackdrop = true,
}: ModalProps) {
  const bodyRef = useRef<HTMLDivElement>(null);
  const returnFocusRef = useRef<Element | null>(null);

  // Only attach portal-related effects while open. Mount/unmount of
  // the portal subtree is the lifecycle boundary for focus management.
  useEffect(() => {
    if (!open) return;
    returnFocusRef.current = document.activeElement;

    // Autofocus first focusable child after paint so Tailwind layout
    // has settled. Falls back to the dialog itself if nothing inside
    // is focusable — the dialog has tabIndex=-1 to accept focus.
    const raf = requestAnimationFrame(() => {
      const first = firstFocusable(bodyRef.current);
      if (first) first.focus();
      else bodyRef.current?.focus();
    });

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key === "Tab") {
        trapFocus(e, bodyRef.current);
      }
    }
    document.addEventListener("keydown", onKey);

    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", onKey);
      const toFocus = returnFocusRef.current;
      if (toFocus instanceof HTMLElement) {
        // Restore focus unless it's since moved away to something
        // meaningful (e.g. user clicked a different element after
        // the modal rendered but before closing).
        toFocus.focus();
      }
    };
  }, [open, onClose]);

  const onBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!dismissOnBackdrop) return;
      if (e.target === e.currentTarget) onClose();
    },
    [dismissOnBackdrop, onClose],
  );

  if (!open) return null;
  // SSR / initial-mount safety: portal target may not exist yet during
  // hydration. Render nothing on that pass; the next client tick the
  // #modal-root div from layout.tsx will be in the DOM.
  if (typeof document === "undefined") return null;
  const target = document.getElementById("modal-root");
  if (!target) return null;

  return createPortal(
    <div
      role="presentation"
      onClick={onBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/60 p-24"
    >
      <div
        ref={bodyRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        className={clsx(
          "max-h-full overflow-hidden rounded-6 border border-line bg-panel shadow-modal focus:outline-none",
          className,
        )}
      >
        {children}
      </div>
    </div>,
    target,
  );
}

// Focusable selector: the same filter @testing-library/tabbable uses,
// minus ancillary extras this app doesn't need.
const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function focusableChildren(container: HTMLElement | null): HTMLElement[] {
  if (!container) return [];
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => !el.hasAttribute("data-focus-skip"),
  );
}

function firstFocusable(container: HTMLElement | null): HTMLElement | null {
  return focusableChildren(container)[0] ?? null;
}

function trapFocus(e: KeyboardEvent, container: HTMLElement | null) {
  const focusables = focusableChildren(container);
  if (focusables.length === 0) {
    // Empty dialog — keep focus on the body itself.
    e.preventDefault();
    container?.focus();
    return;
  }
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  const active = document.activeElement as HTMLElement | null;
  if (e.shiftKey) {
    if (active === first || !container?.contains(active)) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (active === last) {
      e.preventDefault();
      first.focus();
    }
  }
}
