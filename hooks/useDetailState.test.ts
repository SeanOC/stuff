// @vitest-environment jsdom

import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { paramsEqual, useDetailState } from "./useDetailState";
import type { Param, Preset } from "@/lib/scad-params/parse";

const PARAMS: Param[] = [
  { kind: "number", name: "d", shortKey: "d", default: 70 },
  { kind: "number", name: "c", shortKey: "c", default: 0.5 },
  { kind: "boolean", name: "open", shortKey: "o", default: true },
];

const STOCK: Preset[] = [
  { id: "a", label: "Preset A", values: { d: 46, c: 0.25, open: true } },
  { id: "b", label: "Preset B", values: { d: 77, c: 0.75, open: false } },
];

afterEach(() => {
  window.localStorage.clear();
});

describe("paramsEqual", () => {
  it("returns true when all declared params match", () => {
    expect(
      paramsEqual({ d: 46, c: 0.25, open: true }, { d: 46, c: 0.25, open: true }, PARAMS),
    ).toBe(true);
  });

  it("returns false when any declared param differs", () => {
    expect(
      paramsEqual({ d: 46, c: 0.25, open: true }, { d: 47, c: 0.25, open: true }, PARAMS),
    ).toBe(false);
  });

  it("ignores extra keys that aren't declared params", () => {
    expect(
      paramsEqual(
        { d: 46, c: 0.25, open: true, extra: 1 },
        { d: 46, c: 0.25, open: true, other: 2 },
        PARAMS,
      ),
    ).toBe(true);
  });
});

describe("useDetailState — preset binding", () => {
  it("starts with defaults and no active preset", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    expect(result.current.state.params).toEqual({ d: 70, c: 0.5, open: true });
    expect(result.current.state.activePresetId).toBeNull();
    expect(result.current.state.modified).toBe(false);
  });

  it("loadPreset replaces params, sets activePresetId, clears modified", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    act(() => result.current.loadPreset("b"));
    expect(result.current.state.params).toEqual({ d: 77, c: 0.75, open: false });
    expect(result.current.state.activePresetId).toBe("b");
    expect(result.current.state.modified).toBe(false);
  });

  it("setParam flips modified when the active preset no longer matches", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    act(() => result.current.loadPreset("a"));
    expect(result.current.state.modified).toBe(false);
    act(() => result.current.setParam("d", 48));
    expect(result.current.state.modified).toBe(true);
    expect(result.current.state.activePresetId).toBe("a");
  });

  it("loadPresetByIndex maps 1-based to the flat stock+user list", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    act(() => result.current.loadPresetByIndex(2));
    expect(result.current.state.activePresetId).toBe("b");
  });

  it("saveAsPreset persists a user preset and binds it active", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    act(() => result.current.setParam("d", 55));
    act(() => result.current.saveAsPreset("Custom"));
    expect(result.current.userPresets).toHaveLength(1);
    expect(result.current.userPresets[0].label).toBe("Custom");
    expect(result.current.state.activePresetId).toBe(
      result.current.userPresets[0].id,
    );
    expect(result.current.state.modified).toBe(false);
  });

  it("deleteUserPreset removes and detaches the active binding", () => {
    const { result } = renderHook(() =>
      useDetailState({ params: PARAMS, stockPresets: STOCK, slug: "m" }),
    );
    act(() => result.current.saveAsPreset("Custom"));
    const id = result.current.userPresets[0].id;
    expect(result.current.state.activePresetId).toBe(id);
    act(() => result.current.deleteUserPreset(id));
    expect(result.current.userPresets).toHaveLength(0);
    expect(result.current.state.activePresetId).toBeNull();
  });
});
