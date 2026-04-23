// @vitest-environment jsdom

// Smoke test for the stale-token contract. Out-of-order WASM
// completions are the one invariant unit tests can catch that E2E
// can't — by the time we see a regression in the browser it looks
// like "params flicker back and forth" and is painful to bisect.
// Here we force the order deterministically.

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { dimensionsFromStl } from "./useRenderer";
import type { Param } from "@/lib/scad-params/parse";

type RawRenderOutput = {
  ok: boolean; stl?: Uint8Array; errorMessage?: string; wallMs: number;
  filesMounted: number; missing: string[]; stderr: string[];
};

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function defer<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}

const pending: Array<Deferred<RawRenderOutput>> = [];

vi.mock("@/lib/wasm/render", () => ({
  renderToStl: vi.fn(() => {
    const d = defer<RawRenderOutput>();
    pending.push(d);
    return d.promise;
  }),
}));

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  pending.length = 0;
  vi.clearAllMocks();
  vi.useRealTimers();
});

// Render the smallest possible STL: header + tri count + one triangle.
// Writes a real little-endian binary STL so dimensionsFromStl has
// something to measure — phase 2b requires dimensions on every ready
// state, so a blank header-only buffer would yield zeros and mask
// regressions in the tri-walk loop.
function makeStl(markerByte: number, boxMm = 10): Uint8Array {
  const buf = new Uint8Array(84 + 50);
  // Tag the header so B can be distinguished from A even if sizes match.
  buf[0] = markerByte;
  // Triangle count = 1 (little-endian uint32 at byte 80).
  new DataView(buf.buffer).setUint32(80, 1, true);
  // One triangle with vertices at (0,0,0), (boxMm, 0, 0), (0, boxMm, boxMm).
  // Leaves the normal (bytes 84–95) at zeros; dimension code ignores it.
  const dv = new DataView(buf.buffer);
  // Vertex 0: origin (already zero).
  // Vertex 1: (boxMm, 0, 0)
  dv.setFloat32(84 + 12 + 12, boxMm, true);
  // Vertex 2: (0, boxMm, boxMm)
  dv.setFloat32(84 + 12 + 24 + 4, boxMm, true);
  dv.setFloat32(84 + 12 + 24 + 8, boxMm, true);
  return buf;
}

describe("useRenderer — stale token cancellation", () => {
  it("discards slow render A when fast render B resolves first", async () => {
    const { useRenderer } = await import("./useRenderer");

    const params: Param[] = [
      { kind: "number", name: "x", shortKey: "x", default: 1 },
    ];

    const { result, rerender } = renderHook(
      ({ values }: { values: Record<string, number> }) =>
        useRenderer({
          modelPath: "models/test.scad",
          source: "x = 1; // @param number\n",
          params,
          values,
        }),
      { initialProps: { values: { x: 1 } } },
    );

    // Phase 2b (st-psn): nothing fires on mount — user must invoke
    // refresh() (Enter key in the real UI) to kick off the first render.
    act(() => {
      result.current.refresh();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(pending.length).toBe(1);

    // Change values → debounce restarts, new render fires after 250ms.
    rerender({ values: { x: 2 } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(pending.length).toBe(2);

    const [a, b] = pending;
    const stlB = makeStl(0xbb);
    const stlA = makeStl(0xaa);

    // Resolve B first (fast). The hook should accept it.
    await act(async () => {
      b.resolve({
        ok: true, stl: stlB, wallMs: 5,
        filesMounted: 0, missing: [], stderr: [],
      });
    });

    await waitFor(() => {
      expect(result.current.state.kind).toBe("ready");
    });
    const readyB = result.current.state;
    if (readyB.kind !== "ready") throw new Error("expected ready");
    expect(readyB.result.stlBytes[0]).toBe(0xbb);

    // Now resolve A (slow) — token has already advanced past it, so
    // state must NOT revert to A's result.
    await act(async () => {
      a.resolve({
        ok: true, stl: stlA, wallMs: 500,
        filesMounted: 0, missing: [], stderr: [],
      });
      await Promise.resolve();
    });

    const finalState = result.current.state;
    expect(finalState.kind).toBe("ready");
    if (finalState.kind !== "ready") throw new Error("expected ready");
    expect(finalState.result.stlBytes[0]).toBe(0xbb);

    // History should record only the winner.
    expect(result.current.history).toHaveLength(1);
    expect(result.current.history[0].stlBytes[0]).toBe(0xbb);
  });

  it("stays idle on mount until refresh() is called", async () => {
    const { useRenderer } = await import("./useRenderer");
    const { result } = renderHook(() =>
      useRenderer({
        modelPath: "models/test.scad",
        source: "x = 1; // @param number\n",
        params: [{ kind: "number", name: "x", shortKey: "x", default: 1 }],
        values: { x: 1 },
      }),
    );

    // Even after the debounce window closes, no render fires — the
    // idle state is the real initial state.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(pending.length).toBe(0);
    expect(result.current.state.kind).toBe("idle");

    // refresh() kicks the first render. Post-debounce, the call reaches
    // the mocked renderer.
    act(() => {
      result.current.refresh();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(pending.length).toBe(1);
  });
});

describe("dimensionsFromStl", () => {
  it("recovers per-axis extent from a one-triangle fixture", () => {
    // Matches makeStl(0, 10): vertices at (0,0,0), (10,0,0), (0,10,10).
    // Bbox extents: x=10, y=10, z=10.
    const stl = makeStl(0, 10);
    const dims = dimensionsFromStl(stl);
    expect(dims).toEqual({ x: 10, y: 10, z: 10 });
  });

  it("returns zeros for a too-short buffer (never throws)", () => {
    const tiny = new Uint8Array(80); // no triangle data at all
    expect(dimensionsFromStl(tiny)).toEqual({ x: 0, y: 0, z: 0 });
  });

  it("measures a larger two-triangle fixture with a non-trivial bbox", () => {
    // Two triangles stretched to span [-50,80] on X, [-10, 40] on Y,
    // [0, 25] on Z. Verifies the min/max walk runs across all three
    // vertices of every triangle, not just the first one found.
    const buf = new Uint8Array(84 + 2 * 50);
    new DataView(buf.buffer).setUint32(80, 2, true);
    const dv = new DataView(buf.buffer);
    // Triangle 0: vertices (-50, -10, 0), (80, 0, 10), (0, 40, 25)
    const t0 = 84;
    dv.setFloat32(t0 + 12, -50, true);
    dv.setFloat32(t0 + 16, -10, true);
    dv.setFloat32(t0 + 20, 0, true);
    dv.setFloat32(t0 + 24, 80, true);
    dv.setFloat32(t0 + 28, 0, true);
    dv.setFloat32(t0 + 32, 10, true);
    dv.setFloat32(t0 + 36, 0, true);
    dv.setFloat32(t0 + 40, 40, true);
    dv.setFloat32(t0 + 44, 25, true);
    // Triangle 1: leave vertices at origin (0,0,0) × 3 — doesn't move the bbox.
    expect(dimensionsFromStl(buf)).toEqual({ x: 130, y: 50, z: 25 });
  });
});

describe("useRenderer — error state populates RenderError.line", () => {
  it("extracts a line number from stderr and surfaces it on the error state", async () => {
    const { useRenderer } = await import("./useRenderer");

    const params: Param[] = [{ kind: "number", name: "x", shortKey: "x", default: 1 }];
    const { result } = renderHook(() =>
      useRenderer({
        modelPath: "models/test.scad",
        source: "x = 1; // @param number\n",
        params,
        values: { x: 1 },
      }),
    );

    // Phase 2b (st-psn): renders no longer auto-fire — trigger the first.
    act(() => {
      result.current.refresh();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(pending.length).toBe(1);

    // WASM returns an error-shaped result with a parseable stderr.
    await act(async () => {
      pending[0].resolve({
        ok: false,
        wallMs: 12,
        filesMounted: 0,
        missing: [],
        errorMessage: "openscad exit=1",
        stderr: [
          "WARNING: Can't open include <missing.scad>",
          'ERROR: Parser error in file "test.scad", line 42: syntax error',
        ],
      });
    });

    await waitFor(() => {
      expect(result.current.state.kind).toBe("error");
    });
    const errState = result.current.state;
    if (errState.kind !== "error") throw new Error("expected error");
    expect(errState.error.line).toBe(42);
    expect(errState.error.message).toContain("Parser error");
    // Log stays as the full stderr — "view full log" shows this.
    expect(errState.error.log).toContain("WARNING:");
    expect(errState.error.log).toContain("ERROR:");
  });
});
