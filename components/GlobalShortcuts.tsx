"use client";

// Global keyboard shortcuts: ⌘K, ⌘L, ?. A tiny client island so the
// server AppShell doesn't pay for useRouter + useShortcut in its
// bundle. Renders nothing.

import { useRouter } from "next/navigation";
import { useUI } from "@/contexts/UIContext";
import { useShortcut } from "@/hooks/useShortcut";

export function GlobalShortcuts() {
  const router = useRouter();
  const { openModal } = useUI();

  useShortcut("$mod+k", () => openModal({ kind: "palette" }));
  useShortcut("$mod+l", () => router.push("/"));
  useShortcut("?", () => openModal({ kind: "shortcutSheet" }));

  return null;
}
