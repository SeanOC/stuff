// The bake's Blob publish step (pst-scmib), driven by a fixture manifest,
// a fixture baked/ tree and an in-memory store — so it RUNS in CI, where
// nothing is ever baked (unlike function-bundle-budget.test.ts's skips).

import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  RECORD_FILE,
  bakedDownloads,
  main,
  uploadBakedDownloads,
  // @ts-expect-error -- upload-bd-baked.mjs is untyped JS run by node at prebuild
} from "./upload-bd-baked.mjs";

const MANIFEST = {
  schemaVersion: 1,
  models: [
    { slug: "plain", multiColour: false, presets: [{ id: "a" }, { id: "b" }] },
    { slug: "sign", multiColour: true, presets: [{ id: "default" }, { id: "three-colour" }] },
  ],
};

// Every advertised download, plus the per-colour STLs the bake also
// writes (<preset>-<part>.stl) — which must never be uploaded.
const BAKED: Record<string, string> = {
  "plain/a.stl": "plain-a",
  "plain/b.stl": "plain-b",
  "sign/default.stl": "sign-default-stl",
  "sign/default.3mf": "sign-default-3mf",
  "sign/three-colour.stl": "sign-three-stl",
  "sign/three-colour.3mf": "sign-three-3mf",
  "sign/default-base.stl": "per-colour",
  "sign/three-colour-bone.stl": "per-colour",
};

const sha = (s: string) => createHash("sha256").update(Buffer.from(s)).digest("hex");

interface Put {
  pathname: string;
  contentType: string;
}

function fakeStore(existing: Record<string, number> = {}) {
  const blobs = new Map<string, number>(Object.entries(existing));
  const puts: Put[] = [];
  return {
    puts,
    async head(pathname: string) {
      const size = blobs.get(pathname);
      return size === undefined ? null : { url: `https://blob.test/${pathname}`, size };
    },
    async put(pathname: string, bytes: Buffer, contentType: string) {
      if (blobs.has(pathname)) throw new Error(`overwrite refused: ${pathname}`);
      blobs.set(pathname, bytes.byteLength);
      puts.push({ pathname, contentType });
      return { url: `https://blob.test/${pathname}` };
    },
  };
}

let root: string;
let bakedRoot: string;
beforeEach(() => {
  root = fs.mkdtempSync(path.join(os.tmpdir(), "upload-bd-baked-"));
  bakedRoot = path.join(root, "build123d", "baked");
  fs.mkdirSync(path.join(root, "build123d"));
  fs.writeFileSync(path.join(root, "build123d", "manifest.json"), JSON.stringify(MANIFEST));
  for (const [file, body] of Object.entries(BAKED)) {
    fs.mkdirSync(path.dirname(path.join(bakedRoot, file)), { recursive: true });
    fs.writeFileSync(path.join(bakedRoot, file), body);
  }
});
afterEach(() => {
  fs.rmSync(root, { recursive: true, force: true });
});

describe("bakedDownloads", () => {
  it("is every preset's STL plus the 3MF of multiColour models only", () => {
    expect(bakedDownloads(MANIFEST).map((d: { slug: string; preset: string; format: string }) =>
      `${d.slug}/${d.preset}.${d.format}`,
    )).toEqual([
      "plain/a.stl",
      "plain/b.stl",
      "sign/default.stl",
      "sign/default.3mf",
      "sign/three-colour.stl",
      "sign/three-colour.3mf",
    ]);
  });

  it("covers the committed manifest: 34 STL + 7 3MF", () => {
    const manifest = JSON.parse(
      fs.readFileSync(path.resolve(__dirname, "..", "build123d", "manifest.json"), "utf8"),
    );
    const formats = bakedDownloads(manifest).map((d: { format: string }) => d.format);
    expect(formats.filter((f: string) => f === "stl").length).toBe(
      manifest.models.reduce((n: number, m: { presets: unknown[] }) => n + m.presets.length, 0),
    );
    expect(formats.filter((f: string) => f === "3mf").length).toBe(
      manifest.models
        .filter((m: { multiColour?: boolean }) => m.multiColour)
        .reduce((n: number, m: { presets: unknown[] }) => n + m.presets.length, 0),
    );
  });
});

describe("uploadBakedDownloads", () => {
  it("publishes each download under bd-baked/<env>/<sha256>/<slug>-<preset>.<fmt> and records it", async () => {
    const store = fakeStore();
    const { record, uploaded, reused } = await uploadBakedDownloads({
      manifest: MANIFEST,
      bakedRoot,
      env: "production",
      commit: "abc123",
      store,
    });
    expect(uploaded).toBe(6);
    expect(reused).toBe(0);
    expect(record.env).toBe("production");
    expect(record.commit).toBe("abc123");
    expect(Object.keys(record.assets).sort()).toEqual(
      ["plain/a.stl", "plain/b.stl", "sign/default.3mf", "sign/default.stl",
        "sign/three-colour.3mf", "sign/three-colour.stl"],
    );
    const entry = record.assets["sign/default.3mf"];
    const pathname = `bd-baked/production/${sha("sign-default-3mf")}/sign-default.3mf`;
    expect(entry).toEqual({
      url: `https://blob.test/${pathname}`,
      pathname,
      size: "sign-default-3mf".length,
      sha256: sha("sign-default-3mf"),
    });
    // Per-colour STLs are never uploaded (I3).
    expect(store.puts.some((p) => /-(base|bone)\.stl$/.test(p.pathname))).toBe(false);
    expect(store.puts.find((p) => p.pathname.endsWith(".3mf"))?.contentType).toBe("model/3mf");
    expect(store.puts.find((p) => p.pathname.endsWith(".stl"))?.contentType).toBe("application/sla");
  });

  it("namespaces by environment: a preview bake never touches production's keys", async () => {
    const prod = await uploadBakedDownloads({ manifest: MANIFEST, bakedRoot, env: "production", store: fakeStore() });
    const preview = await uploadBakedDownloads({ manifest: MANIFEST, bakedRoot, env: "preview", store: fakeStore() });
    for (const key of Object.keys(prod.record.assets)) {
      expect(prod.record.assets[key].pathname.startsWith("bd-baked/production/")).toBe(true);
      expect(preview.record.assets[key].pathname.startsWith("bd-baked/preview/")).toBe(true);
    }
  });

  it("re-uses an unchanged key instead of overwriting it", async () => {
    const pathname = `bd-baked/production/${sha("plain-a")}/plain-a.stl`;
    const store = fakeStore({ [pathname]: "plain-a".length });
    const { uploaded, reused, record } = await uploadBakedDownloads({
      manifest: MANIFEST, bakedRoot, env: "production", store,
    });
    expect(uploaded).toBe(5);
    expect(reused).toBe(1);
    expect(record.assets["plain/a.stl"].url).toBe(`https://blob.test/${pathname}`);
    expect(store.puts.map((p) => p.pathname)).not.toContain(pathname);
  });

  it("refuses an existing key whose size does not match the bake", async () => {
    const pathname = `bd-baked/production/${sha("plain-a")}/plain-a.stl`;
    await expect(
      uploadBakedDownloads({
        manifest: MANIFEST, bakedRoot, env: "production", store: fakeStore({ [pathname]: 1 }),
      }),
    ).rejects.toThrow(/exists with 1 bytes/);
  });

  it("FAILS when a preset's baked artefact is missing", async () => {
    fs.rmSync(path.join(bakedRoot, "sign", "three-colour.3mf"));
    await expect(
      uploadBakedDownloads({ manifest: MANIFEST, bakedRoot, env: "production", store: fakeStore() }),
    ).rejects.toThrow(/1 baked download\(s\) missing.*sign\/three-colour\.3mf/);
  });
});

describe("main", () => {
  it("writes the record on a Vercel build", async () => {
    const record = await main({
      root,
      environ: { VERCEL_ENV: "production", VERCEL_GIT_COMMIT_SHA: "c0ffee" },
      store: fakeStore(),
    });
    const onDisk = JSON.parse(fs.readFileSync(path.join(bakedRoot, RECORD_FILE), "utf8"));
    expect(onDisk).toEqual(record);
    expect(onDisk.commit).toBe("c0ffee");
  });

  it("off Vercel: uploads nothing and removes a stale record", async () => {
    fs.writeFileSync(path.join(bakedRoot, RECORD_FILE), "{}");
    const store = fakeStore();
    expect(await main({ root, environ: {}, store })).toBeNull();
    expect(store.puts).toEqual([]);
    expect(fs.existsSync(path.join(bakedRoot, RECORD_FILE))).toBe(false);
  });

  it("off Vercel: still FAILS on a missing baked artefact", async () => {
    fs.rmSync(path.join(bakedRoot, "plain", "b.stl"));
    await expect(main({ root, environ: {} })).rejects.toThrow(/plain\/b\.stl/);
  });

  it("on Vercel without BLOB_READ_WRITE_TOKEN: FAILS the build", async () => {
    await expect(main({ root, environ: { VERCEL_ENV: "production" } })).rejects.toThrow(
      /BLOB_READ_WRITE_TOKEN is not set/,
    );
  });
});
