"use client";

// Keyboard shortcut binding. Hand-rolled — one window-level keydown
// listener per call site, a ~2-line chord parser, and a `$mod`
// resolver that picks `metaKey` on Mac and `ctrlKey` elsewhere.
//
// The Binding union is exhaustive: each shortcut the app speaks is
// listed by name, typos fail at compile time, and the later
// ShortcutSheet can hand-enumerate without drift. See phase-3 plan D2.
//
// Input-field guard: bare keys ("g", "1") are suppressed when focus
// is inside a form control, so typing into the param rail doesn't
// toggle the grid. Modifier chords (⌘S, ⌘E) always fire — the user
// wants the shortcut even when typing into a text input.

import { useEffect } from "react";

export const BINDINGS = [
  // Mod chords — palette, library, save, download, copy, preset 1-9
  "$mod+k",
  "$mod+l",
  "$mod+s",
  "$mod+e",
  "$mod+1",
  "$mod+2",
  "$mod+3",
  "$mod+4",
  "$mod+5",
  "$mod+6",
  "$mod+7",
  "$mod+8",
  "$mod+9",
  // Bare keys — viewer controls and dialog primitives
  "1",
  "2",
  "3",
  "g",
  "d",
  "f",
  "r",
  "Enter",
  "Escape",
  "?",
] as const;

export type Binding = (typeof BINDINGS)[number];

interface Opts {
  enabled?: boolean;
  preventDefault?: boolean;
}

interface Parsed {
  mod: boolean;
  shift: boolean;
  alt: boolean;
  key: string;
}

function parse(binding: Binding): Parsed {
  const parts = binding.split("+");
  const out: Parsed = { mod: false, shift: false, alt: false, key: "" };
  for (const p of parts) {
    if (p === "$mod") out.mod = true;
    else if (p === "Shift") out.shift = true;
    else if (p === "Alt") out.alt = true;
    else out.key = p;
  }
  return out;
}

function isInputTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
}

function matchesKey(e: KeyboardEvent, wanted: string): boolean {
  // Single-char keys compare case-insensitively so "g" fires on both
  // "g" and "G" (Shift+g). Named keys ("Enter", "Escape") compare
  // exactly — the browser already normalises them.
  if (wanted.length === 1) {
    return e.key.toLowerCase() === wanted.toLowerCase();
  }
  return e.key === wanted;
}

export function useShortcut(
  binding: Binding,
  handler: (e: KeyboardEvent) => void,
  opts: Opts = {},
): void {
  const { enabled = true, preventDefault = true } = opts;

  useEffect(() => {
    if (!enabled) return;
    const parsed = parse(binding);
    const isChord = parsed.mod || parsed.shift || parsed.alt;

    // Symbol keys like "?" require Shift to type on most layouts.
    // Pinning shiftKey=false for those would make the binding
    // unreachable, so skip the shift check unless the binding is a
    // letter or an explicit named key. Letters ("g" vs Shift+g) and
    // named keys ("Enter") still honour the check.
    const keyIsLetter = /^[a-zA-Z]$/.test(parsed.key);
    const keyIsNamed = parsed.key.length > 1;
    const checkShift = parsed.shift || keyIsLetter || keyIsNamed;

    function onKeyDown(e: KeyboardEvent) {
      // Mod resolution happens per-event to pick up Ctrl on win/linux
      // and Meta on mac without the hook asking who it is.
      const mod = e.metaKey || e.ctrlKey;
      if (parsed.mod !== mod) return;
      if (checkShift && parsed.shift !== e.shiftKey) return;
      if (parsed.alt !== e.altKey) return;
      if (!matchesKey(e, parsed.key)) return;
      // Guard bare keys against form-control typing; always fire chords.
      if (!isChord && isInputTarget(e.target)) return;
      if (preventDefault) e.preventDefault();
      handler(e);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [binding, enabled, preventDefault, handler]);
}
