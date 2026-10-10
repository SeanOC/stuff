"use client";

import { useEffect } from "react";

// Expose completion of a client island's effects without opening UI. Call
// after any listener hooks whose readiness the marker promises. Each name
// belongs to one mounted island; cleanup also handles Strict Mode remounts.
export function useHydrationMarker(name: string): void {
  useEffect(() => {
    const attribute = `data-${name}-ready`;
    document.documentElement.setAttribute(attribute, "true");
    return () => document.documentElement.removeAttribute(attribute);
  }, [name]);
}
