// @vitest-environment jsdom

// Contract tests for the live build123d render driver (pst-qbas). The
// two things unit tests catch that the (opt-in, service-stubbed) E2E
// can't reach deterministically: the stale-token cancel on overlapping
// refreshes, and the 503-vs-other error split that drives the "disabled"
// messaging. fetch is mocked so no service is needed.

import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useBdRenderer } from "./useBdRenderer";

type Deferred<T> = { promise: Promise<T>; resolve: (v: T) => void };
function defer<T>(): Deferred<T> {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

function glbResponse(bytes: Uint8Array, renderMs = "42"): Response {
  return new Response(bytes as unknown as BodyInit, {
    status: 200,
    headers: { "content-type": "model/gltf-binary", "x-render-ms": renderMs },
  });
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useBdRenderer", () => {
  it("POSTs slug+params and lands a ready render with bytes + renderMs", async () => {
    const bytes = new Uint8Array([1, 2, 3, 4]);
    fetchMock.mockResolvedValueOnce(glbResponse(bytes, "77"));

    const { result } = renderHook(() => useBdRenderer("holder-spray-can"));
    act(() => result.current.refresh({ d: 70 }));
    expect(result.current.state.kind).toBe("loading");

    await waitFor(() => expect(result.current.state.kind).toBe("ready"));
    const state = result.current.state;
    if (state.kind !== "ready") throw new Error("expected ready");
    expect(Array.from(state.glb)).toEqual([1, 2, 3, 4]);
    expect(state.renderMs).toBe(77);
    expect(result.current.renderedValues).toEqual({ d: 70 });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/bd-render");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      slug: "holder-spray-can",
      params: { d: 70 },
    });
  });

  it("a stale refresh never clobbers a newer one (token cancel)", async () => {
    const first = defer<Response>();
    const second = defer<Response>();
    fetchMock.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

    const { result } = renderHook(() => useBdRenderer("m"));
    act(() => result.current.refresh({ d: 1 }));
    act(() => result.current.refresh({ d: 2 }));

    // Resolve the SECOND (newest) first, then the stale first.
    await act(async () => {
      second.resolve(glbResponse(new Uint8Array([2])));
      await second.promise;
    });
    await waitFor(() => expect(result.current.state.kind).toBe("ready"));
    expect(result.current.renderedValues).toEqual({ d: 2 });

    await act(async () => {
      first.resolve(glbResponse(new Uint8Array([1])));
      await first.promise;
    });
    // The superseded render must be ignored — snapshot stays on d:2.
    expect(result.current.renderedValues).toEqual({ d: 2 });
    const state = result.current.state;
    if (state.kind !== "ready") throw new Error("expected ready");
    expect(Array.from(state.glb)).toEqual([2]);
  });

  it("marks a 503 as disabled with a friendly message", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "off", disabled: true }), {
        status: 503,
        headers: { "content-type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useBdRenderer("m"));
    act(() => result.current.refresh({}));
    await waitFor(() => expect(result.current.state.kind).toBe("error"));
    const state = result.current.state;
    if (state.kind !== "error") throw new Error("expected error");
    expect(state.disabled).toBe(true);
  });

  it("a 502 is an error but NOT disabled", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "bd-render service failed" }), {
        status: 502,
        headers: { "content-type": "application/json" },
      }),
    );
    const { result } = renderHook(() => useBdRenderer("m"));
    act(() => result.current.refresh({}));
    await waitFor(() => expect(result.current.state.kind).toBe("error"));
    const state = result.current.state;
    if (state.kind !== "error") throw new Error("expected error");
    expect(state.disabled).toBe(false);
  });

  it("reset() drops back to idle and clears the snapshot", async () => {
    fetchMock.mockResolvedValueOnce(glbResponse(new Uint8Array([9])));
    const { result } = renderHook(() => useBdRenderer("m"));
    act(() => result.current.refresh({ d: 5 }));
    await waitFor(() => expect(result.current.state.kind).toBe("ready"));

    act(() => result.current.reset());
    expect(result.current.state.kind).toBe("idle");
    expect(result.current.renderedValues).toBeNull();
  });
});
