// Server-side AppShell composes the Caliper chrome and the client
// islands that handle interactivity. Keeping AppShell itself a
// server component means `children` doesn't ride on the
// client-component bundle — pages and detail routes hydrate on their
// own clocks, not delayed by the palette/shortcut wiring. (st-3lc)

import type { ReactNode } from "react";
import { TopBar } from "./TopBar";
import { GlobalShortcuts } from "./GlobalShortcuts";
import { CommandPalette } from "./CommandPalette";
import { ShortcutSheet } from "./ShortcutSheet";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-text">
      <TopBar />
      <main className="min-w-0">{children}</main>
      <GlobalShortcuts />
      <CommandPalette />
      <ShortcutSheet />
    </div>
  );
}
