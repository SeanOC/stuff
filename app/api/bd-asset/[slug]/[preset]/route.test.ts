// Route-level tests for the build123d baked-preset server (pst-0um9).
// Drives the real GET handler against the committed manifest allowlist
// with tiny fixture files written into the baked root, so no actual
// build123d bake is needed. Covers the security-relevant paths the P1b
// review called out: unknown model, unknown preset, and traversal-shaped
// segments (rejected by the allowlist before any fs access).

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { NextRequest } from "next/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { GET } from "./route";

const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked");
// A model + preset that exist in the committed manifest.json.
const SLUG = "holder-spray-can";
const PRESET = "spray_can";
const STL_BYTES = new Uint8Array([1, 2, 3, 4]);
const GLB_BYTES = new Uint8Array([0x67, 0x6c, 0x54, 0x46]); // "glTF"
// The multi-colour model and the 3MF its L2 bake writes (pst-egc3j).
const LABEL_SLUG = "holder-label-card";
const LABEL_PRESET = "inlaid";
const THREEMF_BYTES = new Uint8Array([0x50, 0x4b, 0x03, 0x04]); // zip "PK"

const FIXTURES = [
  { file: `${SLUG}/${PRESET}.stl`, bytes: STL_BYTES },
  { file: `${SLUG}/${PRESET}.glb`, bytes: GLB_BYTES },
  { file: `${LABEL_SLUG}/${LABEL_PRESET}.3mf`, bytes: THREEMF_BYTES },
];

function installFixtures(root: string): () => void {
  // Snapshot every artifact before writing any fixture, including the STL
  // removed by the missing-bake test. Existing directories are left alone.
  const originals = FIXTURES.map(({ file }) => {
    const target = path.join(root, file);
    return fs.existsSync(target) ? fs.readFileSync(target) : null;
  });
  const createdDirs = [
    ...new Set(FIXTURES.map(({ file }) => path.dirname(path.join(root, file)))),
  ].filter((dir) => !fs.existsSync(dir));
  const restore = () => {
    FIXTURES.forEach(({ file }, index) => {
      const target = path.join(root, file);
      const original = originals[index];
      if (original === null) fs.rmSync(target, { force: true });
      else fs.writeFileSync(target, original);
    });
    // Remove only directories we created, and only when empty.
    for (const dir of createdDirs) {
      if (fs.existsSync(dir)) fs.rmdirSync(dir);
    }
  };
  try {
    for (const { file, bytes } of FIXTURES) {
      const target = path.join(root, file);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, bytes);
    }
  } catch (error) {
    restore();
    throw error;
  }
  return restore;
}

let restoreFixtures: (() => void) | undefined;
beforeAll(() => {
  restoreFixtures = installFixtures(BAKED_ROOT);
});
afterAll(() => {
  restoreFixtures?.();
});

describe("baked fixture cleanup", () => {
  it.each(["existing", "absent", "mixed"])("restores %s artifacts after fixture deletion", (state) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "bd-asset-test-"));
    try {
      const originals = FIXTURES.map(({ file }, index) => {
        if (state === "absent" || (state === "mixed" && index === 1)) return null;
        const bytes = Buffer.from([0, 255, index, 42]);
        const target = path.join(root, file);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, bytes);
        return bytes;
      });
      const restore = installFixtures(root);
      for (const { file, bytes } of FIXTURES) {
        expect(fs.readFileSync(path.join(root, file))).toEqual(Buffer.from(bytes));
      }
      // Exercise the destructive missing-bake case before suite cleanup.
      fs.rmSync(path.join(root, FIXTURES[0].file));
      restore();
      FIXTURES.forEach(({ file }, index) => {
        const target = path.join(root, file);
        if (originals[index] === null) expect(fs.existsSync(target)).toBe(false);
        else expect(fs.readFileSync(target)).toEqual(originals[index]);
      });
      if (state === "absent") expect(fs.readdirSync(root)).toEqual([]);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });
});

async function call(
  slug: string,
  preset: string,
  format?: string,
): Promise<Response> {
  const qs = format === undefined ? "" : `?format=${encodeURIComponent(format)}`;
  const req = new NextRequest(
    `http://localhost/api/bd-asset/${slug}/${preset}${qs}`,
  );
  return GET(req, { params: Promise.resolve({ slug, preset }) });
}

describe("/api/bd-asset", () => {
  it("serves the baked GLB (default format) with the gltf-binary type", async () => {
    const res = await call(SLUG, PRESET);
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("model/gltf-binary");
    // GLB is inline (viewer fetch), not an attachment.
    expect(res.headers.get("content-disposition")).toBeNull();
    // The URL is deploy-stable but the bytes change with geometry/presets,
    // so it must revalidate rather than be cached `immutable` for a year.
    const cc = res.headers.get("cache-control") ?? "";
    expect(cc).toContain("must-revalidate");
    expect(cc).not.toContain("immutable");
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(GLB_BYTES);
  });

  it("serves the baked STL as an attachment download", async () => {
    const res = await call(SLUG, PRESET, "stl");
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("application/sla");
    expect(res.headers.get("content-disposition")).toBe(
      `attachment; filename="${SLUG}-${PRESET}.stl"`,
    );
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(STL_BYTES);
  });

  it("serves a multi-colour model's baked 3MF as an attachment download", async () => {
    const res = await call(LABEL_SLUG, LABEL_PRESET, "3mf");
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toBe("model/3mf");
    expect(res.headers.get("content-disposition")).toBe(
      `attachment; filename="${LABEL_SLUG}-${LABEL_PRESET}.3mf"`,
    );
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(THREEMF_BYTES);
  });

  it("400s a 3MF for a single-colour model (never baked, not a missing bake)", async () => {
    const res = await call(SLUG, PRESET, "3mf");
    expect(res.status).toBe(400);
    expect((await res.json()).error).toContain("not a multi-colour model");
  });

  it("404s an unknown model", async () => {
    const res = await call("no-such-model", PRESET);
    expect(res.status).toBe(404);
    expect((await res.json()).error).toContain("unknown build123d model");
  });

  it("404s an unknown preset for a known model", async () => {
    const res = await call(SLUG, "no-such-preset");
    expect(res.status).toBe(404);
    expect((await res.json()).error).toContain("unknown preset");
  });

  it("400s an unsupported format", async () => {
    const res = await call(SLUG, PRESET, "obj");
    expect(res.status).toBe(400);
    expect((await res.json()).error).toContain("format must be");
  });

  it("rejects path-traversal-shaped segments via the allowlist (no fs escape)", async () => {
    // Neither segment is a manifest slug/preset, so the allowlist 404s
    // before any path is built — the '..' never reaches the filesystem.
    const res = await call("..", "..", "stl");
    expect(res.status).toBe(404);
  });

  it("404s a manifest-valid pair whose asset was never baked", async () => {
    // Remove our fixture to reach ENOENT even when all real presets were
    // baked. Always put it back for later tests; suite cleanup separately
    // restores the original developer artifact (or its absence).
    const stl = path.join(BAKED_ROOT, SLUG, `${PRESET}.stl`);
    fs.rmSync(stl);
    try {
      const res = await call(SLUG, PRESET, "stl");
      expect(res.status).toBe(404);
      expect((await res.json()).error).toContain("baked asset missing");
    } finally {
      fs.writeFileSync(stl, STL_BYTES);
    }
  });
});
