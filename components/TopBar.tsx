"use client";

// Caliper top bar. Small client island because the search button
// dispatches into UIContext. Kept separate from AppShell so the
// layout tree doesn't pay a client-component bundle cost on every
// route. (st-3lc)

import { useUI } from "@/contexts/UIContext";

export function TopBar() {
  const { openModal } = useUI();
  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-panel px-12"
      style={{ height: 38 }}
    >
      <div className="flex items-center gap-12">
        <span
          className="text-11 font-semibold uppercase"
          style={{ letterSpacing: "0.08em" }}
        >
          STUFF
        </span>
        <span className="font-mono text-10 text-text-mute">v0.1</span>
        {/* Breadcrumb slot — populated per-route in phase 1. */}
        <nav className="text-12 text-text-dim" aria-label="breadcrumb" />
      </div>
      <div className="flex items-center gap-10">
        <button
          type="button"
          onClick={() => openModal({ kind: "palette" })}
          className="flex items-center gap-6 rounded-3 border border-line bg-panel2 px-6 py-2 text-11 text-text-dim hover:border-accent-line hover:text-text"
          style={{ height: 22 }}
          aria-label="Open command palette"
        >
          <span>Search</span>
          <kbd
            className="flex items-center justify-center rounded-3 border border-line bg-panel font-mono text-10 text-text-dim"
            style={{ height: 18, padding: "0 5px" }}
          >
            ⌘K
          </kbd>
        </button>
        <span
          aria-label="account"
          className="rounded-full border border-line bg-panel2"
          style={{ width: 18, height: 18 }}
        />
      </div>
    </header>
  );
}
