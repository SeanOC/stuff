"use client";

// Manual WASM render driver, extracted from the monolithic ModelStudio.
// Owns the render state machine (idle / loading / ready / error), a
// token-cancelled effect so stale renders can't clobber a newer
// in-flight one, and a small ring buffer of recent successes the
// detail-page left rail can show as a render log.
//
// Phase-2 change (st-psn): renders don't fire automatically on mount.
// Initial state is `idle` and stays there until `refresh()` is called
// (ViewerChrome wires Enter).
//
// pst-vfp: renders are fully manual — they fire ONLY on `refresh()`, not
// on every param change. Param editing stays instant and unblocked; the
// viewer flags the on-screen render as stale when the live values drift
// from `renderedValues` (the snapshot the displayed render was built
// from). Each `refresh()` snapshots the current values, supersedes any
// in-flight render via the cancel token, and — on success — records that
// snapshot as `renderedValues` so the staleness check has a baseline.

import { useEffect, useRef, useState } from "react";
import {
  applyParamOverrides,
  type Param,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import { parseRenderError } from "@/lib/wasm/render-error";

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

export interface Dimensions {
  x: number;
  y: number;
  z: number;
}

export interface RenderResult {
  stlBytes: Uint8Array;
  triCount: number;
  ms: number;
  dimensions: Dimensions;
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
  /**
   * The param values the currently displayed render was built from, or
   * null before the first successful render. The viewer compares this
   * against the live control values to decide whether the on-screen
   * render is stale. (pst-vfp)
   */
  renderedValues: Record<string, ParamValue> | null;
  refresh: () => void;
}

export function useRenderer(input: RenderInput): UseRendererReturn {
  const { source, params, values } = input;

  // Live refs to the latest inputs. refresh() reads these at click time
  // so a render always reflects whatever is on screen, without listing
  // them in the render effect's deps — which would re-introduce the
  // old auto-render-on-change behavior pst-vfp deliberately removes.
  const sourceRef = useRef(source);
  sourceRef.current = source;
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const valuesRef = useRef(values);
  valuesRef.current = values;

  const [state, setState] = useState<RenderState>({ kind: "idle" });
  const [history, setHistory] = useState<RenderResult[]>([]);
  const [renderedValues, setRenderedValues] = useState<
    Record<string, ParamValue> | null
  >(null);
  const [refreshToken, setRefreshToken] = useState(0);
  const cancelToken = useRef(0);
  // Gates the mount effect: the render only runs once refresh() has
  // fired (bumping refreshToken past its initial 0). Phase 2's "press ⏎
  // to render" idle state depends on this — otherwise the mount-time
  // effect renders before the user asks for it.
  const hasStarted = useRef(false);

  useEffect(() => {
    if (!hasStarted.current) return;
    // Snapshot the live values so the completed render can record
    // exactly what it was built from (the staleness baseline).
    const snapshot = { ...valuesRef.current };
    const sourceWithOverrides = applyParamOverrides(
      sourceRef.current,
      paramsRef.current,
      snapshot,
    );
    const myToken = ++cancelToken.current;
    setState({ kind: "loading", since: performance.now() });
    void renderToStl({
      source: sourceWithOverrides,
      fetchLibFile: fetchLibFromApi,
      fetchAssetFile: fetchAssetFromApi,
    }).then((raw) => {
      if (myToken !== cancelToken.current) return; // stale — a newer render already fired
      if (raw.ok && raw.stl && raw.stl.length > 0) {
        const result: RenderResult = {
          stlBytes: raw.stl,
          triCount: triCountFromStl(raw.stl),
          ms: raw.wallMs,
          dimensions: dimensionsFromStl(raw.stl),
        };
        setState({ kind: "ready", result });
        setHistory((prev) => [result, ...prev].slice(0, HISTORY_MAX));
        // The displayed render now matches this snapshot — clears the
        // stale flag whenever the live values still equal it.
        setRenderedValues(snapshot);
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
        // Leave renderedValues untouched: on error the viewer keeps the
        // last good render on screen, so its snapshot stays the baseline.
      }
    });
  }, [refreshToken]);

  return {
    state,
    history,
    renderedValues,
    refresh: () => {
      hasStarted.current = true;
      setRefreshToken((n) => n + 1);
    },
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

// Binary import() assets (STL meshes) live next to their model under
// models/ — a model's relative import path resolves against that dir.
async function fetchAssetFromApi(relPath: string): Promise<Uint8Array | null> {
  const url = new URL("/api/source", window.location.origin);
  url.searchParams.set("path", `models/${relPath}`);
  const res = await fetch(url.toString());
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`fetch ${relPath}: ${res.status}`);
  return new Uint8Array(await res.arrayBuffer());
}

// Exported for the smoke test — otherwise the token-cancel contract is
// invisible from the outside. Pure function, no state.
//
// OpenSCAD-wasm sometimes writes ASCII STL (starts with "solid "),
// other times binary. Binary can also technically begin with "solid"
// in its 80-byte header, so we can't read the first word alone. The
// reliable tell: in a well-formed binary STL, byteLength ==
// 84 + nTri * 50 where nTri is the uint32 at byte 80. When that
// identity fails, treat the buffer as ASCII.
export function triCountFromStl(bytes: Uint8Array): number {
  if (isBinaryStl(bytes)) {
    return readBinaryTriCount(bytes);
  }
  return countAsciiFacets(bytes);
}

// Compute per-axis extents from an STL. Handles binary and ASCII;
// openscad-wasm is known to emit either depending on build flags.
// Pure function so the stat strip doesn't need three.js. Returns
// zeros on malformed/short input rather than throwing.
export function dimensionsFromStl(bytes: Uint8Array): Dimensions {
  const box = isBinaryStl(bytes)
    ? bboxFromBinaryStl(bytes)
    : bboxFromAsciiStl(bytes);
  if (!box) return { x: 0, y: 0, z: 0 };
  return {
    x: round1(box.max[0] - box.min[0]),
    y: round1(box.max[1] - box.min[1]),
    z: round1(box.max[2] - box.min[2]),
  };
}

function isBinaryStl(bytes: Uint8Array): boolean {
  if (bytes.byteLength < BIN_STL_HEADER_BYTES) return false;
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const claimed = dv.getUint32(80, true);
  return bytes.byteLength === BIN_STL_HEADER_BYTES + claimed * BIN_STL_TRI_BYTES;
}

function readBinaryTriCount(bytes: Uint8Array): number {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return dv.getUint32(80, true);
}

// Binary STL layout per triangle (50 bytes):
//   bytes  0–11   normal (3 × float32)  — ignored for bbox
//   bytes 12–47   v0, v1, v2 vertices (9 × float32)
//   bytes 48–49   attribute byte count (uint16)
function bboxFromBinaryStl(bytes: Uint8Array): Bbox | null {
  const nTri = readBinaryTriCount(bytes);
  if (nTri === 0) return null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  for (let t = 0; t < nTri; t++) {
    const base = BIN_STL_HEADER_BYTES + t * BIN_STL_TRI_BYTES;
    for (let v = 0; v < 3; v++) {
      const o = base + 12 + v * 12;
      const x = view.getFloat32(o, true);
      const y = view.getFloat32(o + 4, true);
      const z = view.getFloat32(o + 8, true);
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
      if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
    }
  }
  return { min: [minX, minY, minZ], max: [maxX, maxY, maxZ] };
}

// ASCII STL uses `vertex X Y Z` lines. A single regex sweep over a
// TextDecoder'd string is plenty fast for our size range (a few MB
// in the hot path) and needs no parser state. Only `vertex` lines
// contribute to the bbox — `normal` and other directives are skipped.
const VERTEX_RE = /vertex\s+(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s+(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;

function bboxFromAsciiStl(bytes: Uint8Array): Bbox | null {
  const text = decodeUtf8(bytes);
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  let any = false;
  VERTEX_RE.lastIndex = 0;
  for (const m of text.matchAll(VERTEX_RE)) {
    any = true;
    const x = Number(m[1]), y = Number(m[2]), z = Number(m[3]);
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
    if (z < minZ) minZ = z; if (z > maxZ) maxZ = z;
  }
  return any ? { min: [minX, minY, minZ], max: [maxX, maxY, maxZ] } : null;
}

function countAsciiFacets(bytes: Uint8Array): number {
  const text = decodeUtf8(bytes);
  let n = 0;
  const re = /facet normal/g;
  while (re.exec(text) !== null) n++;
  return n;
}

function decodeUtf8(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

interface Bbox {
  min: [number, number, number];
  max: [number, number, number];
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
