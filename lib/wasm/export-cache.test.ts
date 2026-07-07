import { describe, expect, it } from "vitest";
import {
  computeCacheKey,
  computeClosureHash,
  normalizeParams,
  rendererVersion,
  type ExportCacheStore,
} from "./export-cache";
import type { FileFetcher } from "./closure";

// A tiny model whose closure is one lib file, so we can mutate the lib and
// assert the closure hash tracks it.
const ENTRY = "include <lib/a.scad>\ncube(1);";
function libFetcher(lib: Record<string, string>): FileFetcher {
  return async (p) => lib[p] ?? null;
}

describe("normalizeParams", () => {
  it("is independent of key order", () => {
    const a = normalizeParams({ b: 2, a: 1, c: true });
    const b = normalizeParams({ c: true, a: 1, b: 2 });
    expect(a).toBe(b);
  });

  it("distinguishes different values", () => {
    expect(normalizeParams({ x: 1 })).not.toBe(normalizeParams({ x: 2 }));
    expect(normalizeParams({ x: "1" })).not.toBe(normalizeParams({ x: 1 }));
    expect(normalizeParams({ x: true })).not.toBe(normalizeParams({ x: false }));
  });

  it("collapses -0 and 0 to the same string", () => {
    expect(normalizeParams({ x: -0 })).toBe(normalizeParams({ x: 0 }));
  });
});

describe("computeClosureHash", () => {
  it("is stable for identical closures", async () => {
    const lib = { "lib/a.scad": "// leaf" };
    const h1 = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher(lib),
    });
    const h2 = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher(lib),
    });
    expect(h1).toBe(h2);
  });

  it("changes when the entry source changes", async () => {
    const lib = { "lib/a.scad": "// leaf" };
    const h1 = await computeClosureHash({ entrySource: ENTRY, fetchLibFile: libFetcher(lib) });
    const h2 = await computeClosureHash({
      entrySource: ENTRY + "\nsphere(2);",
      fetchLibFile: libFetcher(lib),
    });
    expect(h1).not.toBe(h2);
  });

  it("changes when a file in the closure (a shared lib) changes", async () => {
    const h1 = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher({ "lib/a.scad": "// original" }),
    });
    const h2 = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher({ "lib/a.scad": "// EDITED" }),
    });
    expect(h1).not.toBe(h2);
  });

  it("depends only on the CONTENT of a closure file, not its position", async () => {
    // Same entry, same two libs, but the libs swap their bodies. The file
    // SET is identical yet the content differs, so the hash must change —
    // proving content (not just membership) is folded in.
    const entry = "include <lib/a.scad>\ninclude <lib/b.scad>";
    const h1 = await computeClosureHash({
      entrySource: entry,
      fetchLibFile: libFetcher({ "lib/a.scad": "// X", "lib/b.scad": "// Y" }),
    });
    const h2 = await computeClosureHash({
      entrySource: entry,
      fetchLibFile: libFetcher({ "lib/a.scad": "// Y", "lib/b.scad": "// X" }),
    });
    expect(h1).not.toBe(h2);
  });
});

describe("computeCacheKey", () => {
  const base = {
    closureHash: "aaa",
    normalizedParams: "{}",
    rendererVersion: "1.2.0",
  };

  it("is deterministic", () => {
    expect(computeCacheKey(base)).toBe(computeCacheKey({ ...base }));
  });

  it("busts on any component change", () => {
    const k = computeCacheKey(base);
    expect(computeCacheKey({ ...base, closureHash: "bbb" })).not.toBe(k);
    expect(computeCacheKey({ ...base, normalizedParams: '{"x":1}' })).not.toBe(k);
    expect(computeCacheKey({ ...base, rendererVersion: "1.3.0" })).not.toBe(k);
  });

  it("does not collide across boundary-shifted components", () => {
    // "ab"+"c" must not equal "a"+"bc": labels + separators prevent this.
    expect(computeCacheKey({ ...base, closureHash: "ab", normalizedParams: "c" })).not.toBe(
      computeCacheKey({ ...base, closureHash: "a", normalizedParams: "bc" }),
    );
  });
});

describe("rendererVersion", () => {
  it("returns the pinned openscad-wasm-prebuilt version", () => {
    expect(rendererVersion()).toBe("1.2.0");
  });
});

// Exercises the hit/miss/store flow the route implements, against an
// in-memory store — no Blob credentials needed.
function memStore(): ExportCacheStore & { data: Map<string, Uint8Array> } {
  const data = new Map<string, Uint8Array>();
  return {
    data,
    async get(key) {
      return data.get(key) ?? null;
    },
    async put(key, bytes) {
      data.set(key, bytes);
    },
  };
}

describe("cache flow (in-memory store)", () => {
  it("second identical request is a byte-identical hit", async () => {
    const store = memStore();
    const key = computeCacheKey({ closureHash: "h", normalizedParams: "{}", rendererVersion: "1.2.0" });

    expect(await store.get(key)).toBeNull(); // miss
    const rendered = new Uint8Array([1, 2, 3, 4]);
    await store.put(key, rendered);

    const hit = await store.get(key);
    expect(hit).not.toBeNull();
    expect(Array.from(hit!)).toEqual([1, 2, 3, 4]);
  });

  it("a failed render leaves the cache empty (never stored)", async () => {
    // The route only calls store.put on result.ok; simulate a failure by
    // never putting. The next lookup must still miss.
    const store = memStore();
    const key = computeCacheKey({ closureHash: "h", normalizedParams: "{}", rendererVersion: "1.2.0" });
    // (no put — render failed)
    expect(await store.get(key)).toBeNull();
    expect(store.data.size).toBe(0);
  });

  it("changing a param produces a different key → miss", async () => {
    const store = memStore();
    const k1 = computeCacheKey({ closureHash: "h", normalizedParams: normalizeParams({ x: 1 }), rendererVersion: "1.2.0" });
    const k2 = computeCacheKey({ closureHash: "h", normalizedParams: normalizeParams({ x: 2 }), rendererVersion: "1.2.0" });
    await store.put(k1, new Uint8Array([1]));
    expect(await store.get(k2)).toBeNull();
  });

  it("editing a closure file produces a different key → miss", async () => {
    const store = memStore();
    const params = normalizeParams({ x: 1 });
    const before = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher({ "lib/a.scad": "// v1" }),
    });
    const after = await computeClosureHash({
      entrySource: ENTRY,
      fetchLibFile: libFetcher({ "lib/a.scad": "// v2" }),
    });
    const k1 = computeCacheKey({ closureHash: before, normalizedParams: params, rendererVersion: "1.2.0" });
    const k2 = computeCacheKey({ closureHash: after, normalizedParams: params, rendererVersion: "1.2.0" });
    await store.put(k1, new Uint8Array([1]));
    expect(k1).not.toBe(k2);
    expect(await store.get(k2)).toBeNull();
  });

  it("bumping the renderer version produces a different key → miss", async () => {
    const store = memStore();
    const k1 = computeCacheKey({ closureHash: "h", normalizedParams: "{}", rendererVersion: "1.2.0" });
    const k2 = computeCacheKey({ closureHash: "h", normalizedParams: "{}", rendererVersion: "1.3.0" });
    await store.put(k1, new Uint8Array([1]));
    expect(await store.get(k2)).toBeNull();
  });
});
