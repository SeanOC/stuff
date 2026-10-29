// The bake cache's Blob side (pst-aqza2), driven by a fixture plan/bake.json
// and an in-memory store: restore fetches hits, store never overwrites, and
// neither ever throws on a store error (a cache read never fails the build).
// Tarball contents are Python's (build123d/tests/test_bake_cache.py); here
// they are opaque bytes and the round trip is byte-for-byte.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  main,
  restore,
  storeBaked,
  summary,
  // @ts-expect-error -- bd-bake-cache.mjs is untyped JS run by node at prebuild
} from "./bd-bake-cache.mjs";

const ENTRIES = [
  { slug: "plain", preset: "a", key: "k1", pathname: "bd-bake-cache/v1/k1/plain-a.tar.gz" },
  { slug: "plain", preset: "b", key: "k2", pathname: "bd-bake-cache/v1/k2/plain-b.tar.gz" },
  { slug: "sign", preset: "default", key: "k3", pathname: "bd-bake-cache/v1/k3/sign-default.tar.gz" },
];

function fakeStore(existing: Record<string, Buffer> = {}, { failGet = new Set<string>(), failPut = false } = {}) {
  const blobs = new Map<string, Buffer>(Object.entries(existing));
  const puts: string[] = [];
  return {
    blobs,
    puts,
    async head(pathname: string) {
      const bytes = blobs.get(pathname);
      return bytes === undefined ? null : { url: `https://blob.test/${pathname}`, size: bytes.byteLength };
    },
    async get(pathname: string) {
      if (failGet.has(pathname)) throw new Error("socket hang up");
      return blobs.get(pathname) ?? null;
    },
    async put(pathname: string, bytes: Buffer) {
      if (failPut) throw new Error("503");
      if (blobs.has(pathname)) throw new Error(`overwrite refused: ${pathname}`);
      blobs.set(pathname, bytes);
      puts.push(pathname);
      return { url: `https://blob.test/${pathname}` };
    },
  };
}

let dir: string;
const logs: string[] = [];
const log = (line: string) => logs.push(line);
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), "bd-bake-cache-"));
  fs.writeFileSync(path.join(dir, "plan.json"), JSON.stringify({ schema: 1, entries: ENTRIES }));
  logs.length = 0;
});
afterEach(() => {
  fs.rmSync(dir, { recursive: true, force: true });
});

function stage(entries: { pathname: string; key: string }[], hits = 0, bakeSeconds = 12.5) {
  fs.mkdirSync(path.join(dir, "store"), { recursive: true });
  const store = entries.map(({ pathname, key }) => {
    fs.writeFileSync(path.join(dir, "store", `${key}.tar.gz`), Buffer.from(`tar-${key}`));
    return { pathname, file: `store/${key}.tar.gz` };
  });
  fs.writeFileSync(
    path.join(dir, "bake.json"),
    JSON.stringify({ hits, misses: entries.length, bakeSeconds, store }),
  );
}

describe("restore", () => {
  it("writes each existing tarball to fetched/<key>.tar.gz and skips the rest", async () => {
    const store = fakeStore({ [ENTRIES[0].pathname]: Buffer.from("tar-a"), [ENTRIES[2].pathname]: Buffer.from("tar-c") });
    const result = await restore({ dir, store, log });
    expect(result).toMatchObject({ planned: 3, fetched: 2, bytes: 10, errors: 0 });
    expect(fs.readdirSync(path.join(dir, "fetched")).sort()).toEqual(["k1.tar.gz", "k3.tar.gz"]);
    expect(fs.readFileSync(path.join(dir, "fetched", "k3.tar.gz"), "utf8")).toBe("tar-c");
    expect(JSON.parse(fs.readFileSync(path.join(dir, "restore.json"), "utf8"))).toMatchObject({ fetched: 2 });
  });

  it("a fetch error is one log line and a miss, never a throw", async () => {
    const store = fakeStore(
      { [ENTRIES[0].pathname]: Buffer.from("tar-a"), [ENTRIES[1].pathname]: Buffer.from("tar-b") },
      { failGet: new Set([ENTRIES[1].pathname]) },
    );
    const result = await restore({ dir, store, log });
    expect(result).toMatchObject({ fetched: 1, errors: 1 });
    expect(fs.existsSync(path.join(dir, "fetched", "k2.tar.gz"))).toBe(false);
    expect(logs.filter((l) => l.includes("plain/b: fetch failed (socket hang up)"))).toHaveLength(1);
  });
});

describe("storeBaked", () => {
  it("uploads each staged tarball under its planned pathname", async () => {
    stage([ENTRIES[0], ENTRIES[1]]);
    const store = fakeStore();
    expect(await storeBaked({ dir, store, log })).toMatchObject({ staged: 2, stored: 2, failed: 0 });
    expect(store.puts.sort()).toEqual([ENTRIES[0].pathname, ENTRIES[1].pathname]);
    expect(store.blobs.get(ENTRIES[1].pathname)?.toString()).toBe("tar-k2");
  });

  it("never overwrites: an existing same-size key is left alone, a different size warns", async () => {
    stage([ENTRIES[0], ENTRIES[1]]);
    const store = fakeStore({
      [ENTRIES[0].pathname]: Buffer.from("tar-k1"),
      [ENTRIES[1].pathname]: Buffer.from("something else"),
    });
    expect(await storeBaked({ dir, store, log })).toMatchObject({ stored: 0, failed: 1 });
    expect(store.puts).toEqual([]);
    expect(store.blobs.get(ENTRIES[1].pathname)?.toString()).toBe("something else");
    expect(logs.join("\n")).toMatch(/WARN .*plain-b\.tar\.gz exists with 14 bytes, staged 6/);
  });

  it("accepts a key a concurrent build put between head() and put()", async () => {
    stage([ENTRIES[0]]);
    const store = fakeStore();
    let heads = 0;
    const racing = {
      ...store,
      async head(pathname: string) {
        const found = await store.head(pathname);
        // The other build lands its put right after our first head().
        if (heads++ === 0) store.blobs.set(pathname, Buffer.from("tar-k1"));
        return found;
      },
    };
    expect(await storeBaked({ dir, store: racing, log })).toMatchObject({ stored: 0, failed: 0 });
    expect(store.puts).toEqual([]);
  });

  it("a store error warns and continues", async () => {
    stage([ENTRIES[0], ENTRIES[1]]);
    expect(await storeBaked({ dir, store: fakeStore({}, { failPut: true }), log })).toMatchObject({
      stored: 0,
      failed: 2,
    });
    expect(logs.filter((l) => l.startsWith("bake cache: WARN store"))).toHaveLength(2);
  });

  it("nothing staged (an all-hit bake) uploads nothing", async () => {
    stage([], 3);
    const store = fakeStore();
    expect(await storeBaked({ dir, store, log })).toMatchObject({ staged: 0, stored: 0 });
  });
});

describe("round trip", () => {
  it("a stored tarball restores byte-for-byte on the next build", async () => {
    stage([ENTRIES[2]]);
    const store = fakeStore();
    await storeBaked({ dir, store, log });
    fs.rmSync(path.join(dir, "fetched"), { recursive: true, force: true });
    await restore({ dir, store, log });
    expect(fs.readFileSync(path.join(dir, "fetched", "k3.tar.gz"))).toEqual(
      fs.readFileSync(path.join(dir, "store", "k3.tar.gz")),
    );
  });
});

describe("main", () => {
  it("store prints the one-line summary", async () => {
    stage([ENTRIES[0]], 2, 41.25);
    fs.writeFileSync(path.join(dir, "restore.json"), JSON.stringify({ bytes: 3_400_000, seconds: 1.5 }));
    await main({ argv: ["store", dir], store: fakeStore(), log });
    expect(logs.at(-1)).toMatch(
      /^bake cache: 2 hits, 1 misses, 3\.4 MB fetched in 1\.5s, bake 41\.3s, store \d+\.\ds \(1 stored, 0 store failures\)$/,
    );
  });

  it("summary tolerates a skipped restore", () => {
    stage([ENTRIES[0]]);
    expect(summary(dir, { seconds: 0, stored: 1, failed: 0 })).toMatch(/0 hits, 1 misses, 0\.0 MB fetched in 0\.0s/);
  });

  it("refuses to run without a token or a known command", async () => {
    await expect(main({ argv: ["restore", dir], environ: {} })).rejects.toThrow(/BLOB_READ_WRITE_TOKEN/);
    await expect(main({ argv: ["prune", dir], store: fakeStore() })).rejects.toThrow(/usage/);
  });
});
