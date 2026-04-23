// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { useLocalStorage } from "./useLocalStorage";

afterEach(() => {
  window.localStorage.clear();
});

describe("useLocalStorage", () => {
  it("returns the fallback on first render when storage is empty", () => {
    const { result } = renderHook(() =>
      useLocalStorage<number[]>("stuff.v1.empty", []),
    );
    expect(result.current[0]).toEqual([]);
  });

  it("reads a prior value on mount", () => {
    window.localStorage.setItem("stuff.v1.seed", JSON.stringify([1, 2, 3]));
    const { result } = renderHook(() =>
      useLocalStorage<number[]>("stuff.v1.seed", []),
    );
    // useEffect fires synchronously in jsdom after the hook mounts.
    expect(result.current[0]).toEqual([1, 2, 3]);
  });

  it("persists writes and updates in-memory state", () => {
    const { result } = renderHook(() =>
      useLocalStorage<number[]>("stuff.v1.writes", []),
    );
    act(() => {
      result.current[1]([9]);
    });
    expect(result.current[0]).toEqual([9]);
    expect(JSON.parse(window.localStorage.getItem("stuff.v1.writes")!)).toEqual([9]);
  });

  it("accepts a functional updater", () => {
    const { result } = renderHook(() =>
      useLocalStorage<number[]>("stuff.v1.fn", []),
    );
    act(() => {
      result.current[1]((prev) => [...prev, 1]);
    });
    act(() => {
      result.current[1]((prev) => [...prev, 2]);
    });
    expect(result.current[0]).toEqual([1, 2]);
  });

  it("falls back when the stored value is malformed JSON", () => {
    window.localStorage.setItem("stuff.v1.bad", "{not json");
    const { result } = renderHook(() =>
      useLocalStorage<number[]>("stuff.v1.bad", [0]),
    );
    expect(result.current[0]).toEqual([0]);
  });
});
