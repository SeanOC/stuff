// @vitest-environment jsdom

// Smoke test for the stale-token contract. Out-of-order WASM
// completions are the one invariant unit tests can catch that E2E
// can't — by the time we see a regression in the browser it looks
// like "params flicker back and forth" and is painful to bisect.
// Here we force the order deterministically.

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
function makeStl(markerByte: number): Uint8Array {
  const buf = new Uint8Array(84 + 50);
  // Tag the header so B can be distinguished from A even if sizes match.
  buf[0] = markerByte;
  // triangle count = 1
  buf[80] = 1;
  return buf;
}

describe("useRenderer — stale token cancellation", () => {
  it("discards slow render A when fast render B resolves first", async () => {
    const { useRenderer } = await import("./useRenderer");

    const params: Param[] = [
      { kind: "number", name: "x", default: 1 },
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

    // Step past the 250ms debounce so render A fires.
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
});

describe("useRenderer — error state populates RenderError.line", () => {
  it("extracts a line number from stderr and surfaces it on the error state", async () => {
    const { useRenderer } = await import("./useRenderer");

    const params: Param[] = [{ kind: "number", name: "x", default: 1 }];
    const { result } = renderHook(() =>
      useRenderer({
        modelPath: "models/test.scad",
        source: "x = 1; // @param number\n",
        params,
        values: { x: 1 },
      }),
    );

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
