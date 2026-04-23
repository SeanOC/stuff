"use client";

// SSR-safe localStorage binding. On first render returns the fallback;
// a useEffect reads the stored value on the client and replaces state
// if present. Writes go through setValue as usual.
//
// Keys in phase 3 all live under the `stuff.v1.` prefix so future
// migrations don't need a repo-wide rename (see phase-3 plan D3).

import { useCallback, useEffect, useState } from "react";

export function useLocalStorage<T>(
  key: string,
  fallback: T,
): [T, (next: T | ((prev: T) => T)) => void] {
  const [value, setValue] = useState<T>(fallback);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw == null) return;
      setValue(JSON.parse(raw) as T);
    } catch {
      // Malformed entry or privacy-mode-blocked storage — fall back to
      // the default rather than crashing the page. Next write will
      // overwrite the bad value.
    }
  }, [key]);

  const set = useCallback(
    (next: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const resolved =
          typeof next === "function" ? (next as (p: T) => T)(prev) : next;
        try {
          window.localStorage.setItem(key, JSON.stringify(resolved));
        } catch {
          // Quota / privacy — swallow. In-memory state is still
          // updated, so the current session works; persistence is
          // best-effort.
        }
        return resolved;
      });
    },
    [key],
  );

  return [value, set];
}
