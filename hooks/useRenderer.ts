"use client";

// Debounced WASM render driver, extracted from the monolithic
// ModelStudio. Owns the render state machine (idle / loading / ready /
// error), a token-cancelled effect so stale renders can't clobber a
// newer in-flight one, and a small ring buffer of recent successes the
// detail-page left rail can show as a render log.

import { useEffect, useMemo, useRef, useState } from "react";
import {
  applyParamOverrides,
  type Param,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import { parseRenderError } from "@/lib/wasm/render-error";

const RENDER_DEBOUNCE_MS = 250;
const HISTORY_MAX = 5;
// Binary STL layout: 80-byte header + uint32 triangle count + 50 bytes
// per triangle. Recover the count from byte length when the header's
// own count field is unreliable (some writers leave it zero).
const BIN_STL_HEADER_BYTES = 84;
const BIN_STL_TRI_BYTES = 50;

export interface RenderInput {
  modelPath: string;
  source: string;
  params: Param[];
  values: Record<string, ParamValue>;
}

export interface RenderResult {
  stlBytes: Uint8Array;
  triCount: number;
  ms: number;
}

export interface RenderError {
  line: number | null;
  message: string;
  log: string;
}

export type RenderState =
  | { kind: "idle" }
  | { kind: "loading"; since: number }
  | { kind: "ready"; result: RenderResult }
  | { kind: "error"; error: RenderError };

export interface UseRendererReturn {
  state: RenderState;
  history: RenderResult[];
  refresh: () => void;
}

export function useRenderer(input: RenderInput): UseRendererReturn {
  const { source, params, values } = input;

  // Debounce the raw values map so rapid slider drags don't fire a
  // render per tick — matches the 250ms pause the monolithic version
  // used. (modelPath isn't debounced: route changes are rare and the
  // user expects immediate re-render.)
  const [debouncedValues, setDebouncedValues] = useState(values);
  useEffect(() => {
    const id = setTimeout(() => setDebouncedValues(values), RENDER_DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [values]);

  const sourceWithOverrides = useMemo(
    () => applyParamOverrides(source, params, debouncedValues),
    [source, params, debouncedValues],
  );

  const [state, setState] = useState<RenderState>({ kind: "idle" });
  const [history, setHistory] = useState<RenderResult[]>([]);
  const [refreshToken, setRefreshToken] = useState(0);
  const cancelToken = useRef(0);

  useEffect(() => {
    const myToken = ++cancelToken.current;
    setState({ kind: "loading", since: performance.now() });
    void renderToStl({
      source: sourceWithOverrides,
      fetchLibFile: fetchLibFromApi,
    }).then((raw) => {
      if (myToken !== cancelToken.current) return; // stale — a newer render already fired
      if (raw.ok && raw.stl && raw.stl.length > 0) {
        const result: RenderResult = {
          stlBytes: raw.stl,
          triCount: triCountFromStl(raw.stl),
          ms: raw.wallMs,
        };
        setState({ kind: "ready", result });
        setHistory((prev) => [result, ...prev].slice(0, HISTORY_MAX));
      } else {
        const log = raw.stderr.join("\n");
        // parseRenderError looks for the first ERROR: line in stderr
        // and extracts a `line N` reference if present. Phase 2a
        // (st-bg4) — earlier phases left line=null and message as the
        // generic `errorMessage`. Fall back to those if stderr has
        // nothing parseable (rare: WASM-level aborts).
        const parsed = parseRenderError(log);
        setState({
          kind: "error",
          error: {
            line: parsed?.line ?? null,
            message: parsed?.message ?? raw.errorMessage ?? "render failed",
            log,
          },
        });
      }
    });
  }, [sourceWithOverrides, refreshToken]);

  return {
    state,
    history,
    refresh: () => setRefreshToken((n) => n + 1),
  };
}

// Browser-side fetcher used by the closure walker. Don't pre-encode
// the path — searchParams handles it, and the server route's allow
// regex expects literal slashes.
async function fetchLibFromApi(relPath: string): Promise<string | null> {
  const url = new URL("/api/source", window.location.origin);
  url.searchParams.set("path", `libs/${relPath}`);
  const res = await fetch(url.toString());
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`fetch ${relPath}: ${res.status}`);
  return res.text();
}

// Exported for the smoke test — otherwise the token-cancel contract is
// invisible from the outside. Pure function, no state.
export function triCountFromStl(bytes: Uint8Array): number {
  if (bytes.byteLength < BIN_STL_HEADER_BYTES) return 0;
  return Math.max(0, Math.floor((bytes.byteLength - BIN_STL_HEADER_BYTES) / BIN_STL_TRI_BYTES));
}
