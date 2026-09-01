"use client";

// Live build123d render driver (bead pst-qbas, P2c of epic pst-7srz).
//
// The build123d analogue of hooks/useRenderer.ts, but crossing the
// network instead of running WASM in the browser: build123d is Python/
// OCP and can only render in the bd-render Cloud Run service, reached via
// /api/bd-render. There is NO in-browser fallback — a service failure is
// a clean, surfaced error, never a silent degrade.
//
// Manual refresh, exactly like the SCAD viewer's pst-vfp decision: a
// render fires ONLY on refresh() (an Update/Enter action), never on every
// param change. Param editing stays instant; the detail page flags the
// on-screen geometry as stale when the live values drift from
// `renderedValues` (the snapshot the displayed render was built from).
//
// Preset views never touch this hook: the detail page shows the baked
// preset GLB (via /api/bd-asset) and only calls refresh() once a param is
// tweaked. reset() drops back to the idle (preset) state — e.g. when a
// preset is (re)selected — superseding any in-flight render.

import { useCallback, useRef, useState } from "react";
import type { ParamValue } from "@/lib/scad-params/parse";

export type BdRenderState =
  | { kind: "idle" }
  | { kind: "loading"; since: number }
  | { kind: "ready"; glb: Uint8Array; seq: number; renderMs: number | null }
  | { kind: "error"; message: string; disabled: boolean };

export interface UseBdRendererReturn {
  state: BdRenderState;
  /**
   * The live param values the most recent successful render was built
   * from, or null before the first one. The detail page compares this
   * against the current controls to decide staleness. Persists across a
   * later loading/error so the last-good geometry stays the baseline.
   */
  renderedValues: Record<string, ParamValue> | null;
  /** Fire a live render for `values` (Update/Enter). Token-cancelled. */
  refresh: (values: Record<string, ParamValue>) => void;
  /** Drop back to idle (preset view), cancelling any in-flight render. */
  reset: () => void;
}

export function useBdRenderer(slug: string): UseBdRendererReturn {
  const [state, setState] = useState<BdRenderState>({ kind: "idle" });
  const [renderedValues, setRenderedValues] = useState<
    Record<string, ParamValue> | null
  >(null);
  // Supersedes stale in-flight renders: a newer refresh() (or a reset())
  // bumps the token so an earlier fetch's resolution is ignored.
  const cancelToken = useRef(0);
  // Monotonic sequence stamped onto each success so the viewer can key a
  // clean remount per render even when two renders yield equal bytes.
  const seqRef = useRef(0);

  const refresh = useCallback(
    (values: Record<string, ParamValue>) => {
      const snapshot = { ...values };
      const myToken = ++cancelToken.current;
      setState({ kind: "loading", since: Date.now() });
      void (async () => {
        try {
          const res = await fetch("/api/bd-render", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ slug, params: snapshot }),
          });
          if (myToken !== cancelToken.current) return; // superseded
          if (!res.ok) {
            // 503 = feature dark / service unconfigured — a distinct,
            // friendlier message than a genuine render failure (502/4xx).
            const disabled = res.status === 503;
            let message =
              res.status === 503
                ? "Live rendering is currently unavailable."
                : `Render failed (HTTP ${res.status}).`;
            try {
              const body = await res.json();
              if (typeof body?.error === "string") message = body.error;
            } catch {
              /* keep the status-based message */
            }
            setState({ kind: "error", message, disabled });
            return;
          }
          const glb = new Uint8Array(await res.arrayBuffer());
          if (myToken !== cancelToken.current) return; // superseded mid-body
          const renderMsHeader = res.headers.get("x-render-ms");
          setState({
            kind: "ready",
            glb,
            seq: ++seqRef.current,
            renderMs: renderMsHeader ? Number(renderMsHeader) : null,
          });
          setRenderedValues(snapshot);
        } catch (e) {
          if (myToken !== cancelToken.current) return;
          setState({
            kind: "error",
            message:
              e instanceof Error
                ? `Couldn't reach the render service: ${e.message}`
                : "Couldn't reach the render service.",
            disabled: false,
          });
        }
      })();
    },
    [slug],
  );

  const reset = useCallback(() => {
    cancelToken.current++; // supersede any in-flight render
    setState({ kind: "idle" });
    setRenderedValues(null);
  }, []);

  return { state, renderedValues, refresh, reset };
}
