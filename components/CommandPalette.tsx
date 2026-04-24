"use client";

// Hand-rolled command palette (⌘K). Modal 560 px wide. Commands are
// built inline via useMemo — the spec's catalog size doesn't justify
// a separate lib/palette/commands.ts (phase-3 plan D13).
//
// Spec group order: Models · Actions · Presets · Recent. Substring
// filter over label + blurb across all groups, case-insensitive;
// empty query shows everything.
//
// Keyboard: ↑↓ move the cursor (wraps across groups), Enter activates,
// Escape closes. Mouse hover moves the cursor; click activates.

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import clsx from "clsx";
import { Modal } from "./Modal";
import { useUI } from "@/contexts/UIContext";
import type { Binding } from "@/hooks/useShortcut";

export interface PaletteModel {
  slug: string;
  title: string;
  stem: string;
  blurb: string;
}

interface Command {
  id: string;
  label: string;
  blurb?: string;
  hint?: Binding;
  action: () => void;
  enabled: boolean;
}

interface Group {
  id: "models" | "actions" | "presets" | "recent";
  label: string;
  items: Command[];
}

const RECENT_KEY = "stuff.v1.recent.models";
const RECENT_MAX = 5;

export function CommandPalette() {
  const { modal, closeModal, openModal, detail } = useUI();
  const router = useRouter();
  const open = modal.kind === "palette";
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const [models, setModels] = useState<PaletteModel[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset query + cursor each time the palette opens so "recent search
  // terms" don't bleed across sessions. Focus the input on open — the
  // Modal handles first-focusable already, but the input is wrapped in
  // a header div so we tick focus explicitly on the next paint.
  //
  // The models fetch is lazy: first open kicks it off, subsequent
  // opens reuse the cached list (we don't bust on route changes; the
  // catalog is build-time-stable for the palette's purposes).
  useEffect(() => {
    if (!open) return;
    setQuery("");
    setCursor(0);
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  useEffect(() => {
    if (!open || models.length > 0) return;
    let cancelled = false;
    void fetch("/api/models")
      .then((r) => r.json())
      .then((data: { models: PaletteModel[] }) => {
        if (!cancelled) setModels(data.models);
      })
      .catch(() => {
        // Network failure — palette still renders Actions group etc.
      });
    return () => {
      cancelled = true;
    };
  }, [open, models.length]);

  const recentSlugs = useRecentSlugs(open);

  const groups = useMemo(() => {
    const modelCmds: Command[] = models.map((m) => ({
      id: `model:${m.slug}`,
      label: `Go to ${m.title}`,
      blurb: m.stem,
      action: () => {
        router.push(`/models/${m.slug}`);
        closeModal();
      },
      enabled: true,
    }));

    const actionCmds: Command[] = [
      {
        id: "action:download",
        label: "Download STL",
        blurb: detail
          ? detail.canDownload
            ? "Export the current render"
            : "(waiting for first render)"
          : "(open a model first)",
        hint: "$mod+e",
        action: () => {
          detail?.downloadStl();
          closeModal();
        },
        enabled: !!detail?.canDownload,
      },
      {
        id: "action:save-preset",
        label: "Save preset",
        blurb: detail
          ? "Capture the current param values"
          : "(open a model first)",
        hint: "$mod+s",
        action: () => {
          detail?.openSaveRow();
          closeModal();
        },
        enabled: !!detail,
      },
      {
        id: "action:copy-share",
        label: "Copy share link",
        blurb: "Copy the current URL to the clipboard",
        hint: "$mod+Shift+c",
        action: () => {
          void copyShareLink();
          closeModal();
        },
        enabled: typeof window !== "undefined",
      },
      {
        id: "action:shortcuts",
        label: "Open shortcut sheet",
        blurb: "Keyboard reference for every Caliper binding",
        hint: "?",
        action: () => openModal({ kind: "shortcutSheet" }),
        enabled: true,
      },
      {
        id: "action:library",
        label: "Go to library",
        blurb: "Back to the model gallery",
        hint: "$mod+l",
        action: () => {
          router.push("/");
          closeModal();
        },
        enabled: true,
      },
    ];

    const presetCmds: Command[] = (detail?.presets ?? []).map((p, i) => ({
      id: `preset:${p.id}`,
      label: p.label,
      blurb: p.isUser ? "user preset" : "stock preset",
      hint: i < 9 ? (`$mod+${i + 1}` as Binding) : undefined,
      action: () => {
        detail?.loadPreset(p.id);
        closeModal();
      },
      enabled: true,
    }));

    const recentCmds: Command[] = recentSlugs
      .map((slug) => models.find((m) => m.slug === slug))
      .filter((m): m is PaletteModel => !!m)
      .map((m) => ({
        id: `recent:${m.slug}`,
        label: m.title,
        blurb: m.stem,
        action: () => {
          router.push(`/models/${m.slug}`);
          closeModal();
        },
        enabled: true,
      }));

    const out: Group[] = [
      { id: "models", label: "Models", items: modelCmds },
      { id: "actions", label: "Actions", items: actionCmds },
      { id: "presets", label: "Presets", items: presetCmds },
      { id: "recent", label: "Recent", items: recentCmds },
    ];
    return out;
  }, [models, detail, recentSlugs, router, closeModal, openModal]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups.filter((g) => g.items.length > 0);
    return groups
      .map((g) => ({
        ...g,
        items: g.items.filter((c) =>
          `${c.label} ${c.blurb ?? ""}`.toLowerCase().includes(q),
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [groups, query]);

  // Flat list of commands in display order for ↑↓ / Enter arithmetic.
  const flat = useMemo(() => filtered.flatMap((g) => g.items), [filtered]);
  const total = flat.length;

  // Keep cursor in range when the filtered list shrinks under it.
  useEffect(() => {
    if (cursor >= total) setCursor(total === 0 ? 0 : total - 1);
  }, [total, cursor]);

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (total > 0) setCursor((c) => (c + 1) % total);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (total > 0) setCursor((c) => (c - 1 + total) % total);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const cmd = flat[cursor];
      if (cmd && cmd.enabled) cmd.action();
    }
  }

  return (
    <Modal
      open={open}
      onClose={closeModal}
      label="Command palette"
      className="w-[560px]"
    >
      <div onKeyDown={handleKey} className="flex flex-col">
        <header className="flex items-center gap-10 border-b border-line px-14 py-10">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setCursor(0);
            }}
            placeholder="Search or run a command…"
            aria-label="Command search"
            className={clsx(
              "flex-1 bg-transparent font-mono text-12 text-text outline-none",
              "placeholder:text-text-mute",
            )}
          />
          <kbd
            className={clsx(
              "rounded-3 border border-line bg-panel2 px-4 py-1",
              "font-mono text-10 text-text-dim",
            )}
          >
            esc
          </kbd>
        </header>

        <div className="max-h-[420px] overflow-y-auto">
          {filtered.length === 0 && (
            <p className="px-14 py-14 font-mono text-11 text-text-mute">
              No matches.
            </p>
          )}
          {filtered.map((g) => (
            <section key={g.id} data-testid={`palette-group-${g.id}`}>
              <h3
                className={clsx(
                  "px-14 pb-4 pt-12",
                  "font-mono text-10 uppercase tracking-wide text-text-mute",
                )}
              >
                {g.label}
              </h3>
              <ul role="listbox">
                {g.items.map((cmd) => {
                  const flatIndex = flat.indexOf(cmd);
                  const selected = flatIndex === cursor;
                  return (
                    <li key={cmd.id}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={selected}
                        disabled={!cmd.enabled}
                        onMouseEnter={() => setCursor(flatIndex)}
                        onClick={() => {
                          if (cmd.enabled) cmd.action();
                        }}
                        data-testid={`palette-cmd-${cmd.id}`}
                        className={clsx(
                          "flex w-full items-center gap-10 px-14 py-8 text-left",
                          "text-12 text-text",
                          selected
                            ? "bg-accent-soft"
                            : "hover:bg-panel-hi",
                          !cmd.enabled && "opacity-50",
                        )}
                      >
                        <span className="flex-1 min-w-0">
                          <span className="block truncate">{cmd.label}</span>
                          {cmd.blurb && (
                            <span className="block truncate font-mono text-10 text-text-mute">
                              {cmd.blurb}
                            </span>
                          )}
                        </span>
                        {cmd.hint && (
                          <kbd
                            className={clsx(
                              "shrink-0 rounded-3 border border-line bg-panel2 px-4 py-1",
                              "font-mono text-10 text-text-dim",
                            )}
                          >
                            {formatHint(cmd.hint)}
                          </kbd>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>

        <footer
          className={clsx(
            "flex items-center justify-between border-t border-line px-14 py-8",
            "font-mono text-10 text-text-mute",
          )}
        >
          <span>↑↓ navigate · ↵ open</span>
          <span>
            {total} {total === 1 ? "result" : "results"}
          </span>
        </footer>
      </div>
    </Modal>
  );
}

// Render a Binding string the way the user sees it on their OS.
// The useShortcut parser already handles the platform fork; this is
// just pretty-printing for the kbd hint.
function formatHint(b: Binding): string {
  const mac =
    typeof navigator !== "undefined" && /Mac|iPhone|iPad/i.test(navigator.platform);
  return b
    .replace("$mod", mac ? "⌘" : "Ctrl")
    .replace("Shift", "⇧")
    .replace(/\+/g, "")
    .toLowerCase()
    .replace(/^(ctrl|⌘|⇧)/, (s) => s.toUpperCase());
}

async function copyShareLink(): Promise<void> {
  if (typeof navigator === "undefined" || !navigator.clipboard) return;
  try {
    await navigator.clipboard.writeText(window.location.href);
  } catch {
    // Silent — browser permission denial or HTTP page.
  }
}

function useRecentSlugs(open: boolean): string[] {
  const [slugs, setSlugs] = useState<string[]>([]);
  useEffect(() => {
    if (!open) return;
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed)) {
        setSlugs(
          parsed
            .filter((s): s is string => typeof s === "string")
            .slice(0, RECENT_MAX),
        );
      }
    } catch {
      // bad JSON — treat as empty
      setSlugs([]);
    }
  }, [open]);
  return slugs;
}
