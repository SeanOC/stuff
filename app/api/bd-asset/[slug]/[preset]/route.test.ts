// Route-level tests for the build123d baked-preset server (pst-0um9).
// Drives the real GET handler against the committed manifest allowlist
// with tiny fixture files written into the baked root, so no actual
// build123d bake is needed. Covers the security-relevant paths the P1b
// review called out: unknown model, unknown preset, and traversal-shaped
// segments (rejected by the allowlist before any fs access).

import fs from "node:fs";
import path from "node:path";
import { NextRequest } from "next/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { GET } from "./route";

const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked");
// A model + preset that exist in the committed manifest.json.
const SLUG = "holder-spray-can";
const PRESET = "spray_can";
const STL_BYTES = new Uint8Array([1, 2, 3, 4]);
const GLB_BYTES = new Uint8Array([0x67, 0x6c, 0x54, 0x46]); // "glTF"

let createdDir: string | null = null;

beforeAll(() => {
  const dir = path.join(BAKED_ROOT, SLUG);
  // Remember whether we created the dir so cleanup never nukes a real bake.
  if (!fs.existsSync(dir)) createdDir = dir;
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, `${PRESET}.stl`), STL_BYTES);
  fs.writeFileSync(path.join(dir, `${PRESET}.glb`), GLB_BYTES);
});

afterAll(() => {
  // Only remove the fixtures we wrote; leave a developer's real bake alone.
  const dir = path.join(BAKED_ROOT, SLUG);
  fs.rmSync(path.join(dir, `${PRESET}.stl`), { force: true });
  fs.rmSync(path.join(dir, `${PRESET}.glb`), { force: true });
  if (createdDir) fs.rmSync(createdDir, { recursive: true, force: true });
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
    // Remove one fixture we own so this is deterministic regardless of
    // any ambient local bake, then request that missing format. The
    // pair is a valid manifest entry, so it passes the allowlist and
    // hits the ENOENT branch. (beforeAll wrote it; afterAll rm is
    // force:true so double-removal is fine.)
    fs.rmSync(path.join(BAKED_ROOT, SLUG, `${PRESET}.stl`), { force: true });
    const res = await call(SLUG, PRESET, "stl");
    expect(res.status).toBe(404);
    expect((await res.json()).error).toContain("baked asset missing");
    // Restore for any later reads (currently none, but keep it hermetic).
    fs.writeFileSync(path.join(BAKED_ROOT, SLUG, `${PRESET}.stl`), STL_BYTES);
  });
});
