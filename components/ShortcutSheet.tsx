"use client";

// Static keyboard-binding reference sheet (`?`). Spec-authoritative
// source: docs/design/caliper/screenshots/10-shortcuts-reference.png.
// No coupling to useShortcut call sites — phase-3 plan D13 picks the
// "keep in sync manually" trade-off for ~15 bindings. If a binding
// changes in hooks/useShortcut.ts or a DetailPage useShortcut call,
// update the ENTRIES below to match.

import clsx from "clsx";
import { Modal } from "./Modal";
import { useUI } from "@/contexts/UIContext";

interface Row {
  keys: string[];
  label: string;
}

interface Section {
  label: string;
  rows: Row[];
}

const SECTIONS: Section[] = [
  {
    label: "Global",
    rows: [
      { keys: ["⌘", "K"], label: "Command palette" },
      { keys: ["⌘", "L"], label: "Go to library" },
      { keys: ["?"], label: "This shortcut sheet" },
      { keys: ["Esc"], label: "Close modal" },
    ],
  },
  {
    label: "Model",
    rows: [
      { keys: ["⌘", "E"], label: "Download STL" },
      { keys: ["⌘", "S"], label: "Save preset" },
    ],
  },
  {
    label: "Viewer",
    rows: [
      { keys: ["1"], label: "Top view" },
      { keys: ["2"], label: "Front view" },
      { keys: ["3"], label: "Iso view" },
      { keys: ["G"], label: "Toggle grid" },
      { keys: ["D"], label: "Toggle dimensions" },
      { keys: ["F"], label: "Fullscreen viewer" },
      { keys: ["R"], label: "Reset camera" },
      { keys: ["↵"], label: "Render / refresh" },
    ],
  },
  {
    label: "Presets",
    rows: [
      { keys: ["⌘", "1"], label: "Load preset 1" },
      { keys: ["⌘", "2–9"], label: "Load presets 2–9 by index" },
    ],
  },
];

export function ShortcutSheet() {
  const { modal, closeModal } = useUI();
  return (
    <Modal
      open={modal.kind === "shortcutSheet"}
      onClose={closeModal}
      label="Keyboard shortcuts"
      className="w-[560px]"
    >
      <div className="flex flex-col">
        <header className="flex items-center justify-between border-b border-line px-14 py-10">
          <h2
            className={clsx(
              "m-0 font-mono text-11 uppercase tracking-wide text-text-dim",
            )}
          >
            Keyboard shortcuts
          </h2>
          <button
            type="button"
            onClick={closeModal}
            aria-label="Close shortcut sheet"
            className="font-mono text-11 text-text-dim hover:text-text"
          >
            esc
          </button>
        </header>
        <div
          className={clsx(
            "max-h-[520px] overflow-y-auto px-14 py-12",
            "grid grid-cols-2 gap-x-24 gap-y-18",
          )}
        >
          {SECTIONS.map((s) => (
            <section key={s.label} data-testid={`shortcut-section-${s.label.toLowerCase()}`}>
              <h3
                className={clsx(
                  "mb-6 font-mono text-10 uppercase tracking-wide text-text-mute",
                )}
              >
                {s.label}
              </h3>
              <ul className="flex flex-col gap-6">
                {s.rows.map((r, i) => (
                  <li
                    key={`${s.label}-${i}`}
                    className="flex items-center justify-between gap-10 text-12 text-text"
                  >
                    <span className="truncate">{r.label}</span>
                    <span className="flex shrink-0 items-center gap-2">
                      {r.keys.map((k, j) => (
                        <kbd
                          key={j}
                          className={clsx(
                            "rounded-3 border border-line bg-panel2 px-4 py-1",
                            "font-mono text-10 text-text-dim",
                          )}
                        >
                          {k}
                        </kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </Modal>
  );
}
