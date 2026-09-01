// build123d baked-preset asset server (bead pst-0um9, epic pst-7srz).
//
// Serves the build-time-baked STL/GLB for one (model, preset) pair:
//   GET /api/bd-asset/<slug>/<preset>?format=glb   → viewer geometry
//   GET /api/bd-asset/<slug>/<preset>?format=stl   → print download
//
// This is the P1 preset flow — NOT /api/export. There is no live
// rendering here; the files were baked by scripts/bake-bd-presets.sh
// (build123d/scripts/export.py --presets-only) into BAKED_ROOT during
// the build. The download is that baked STL verbatim.
//
// Allowlist, not path arithmetic. slug + preset are looked up in the
// committed manifest (build123d/manifest.json). A request for a model
// or preset the manifest doesn't declare is a 404 before any path is
// built — so nothing an attacker controls ever reaches the filesystem
// as a raw segment. Defense in depth: after building the path from the
// matched (already SAFE_ID_RE-validated) slug/preset, we still confirm
// the resolved path stays under BAKED_ROOT.

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";
import { loadBdModel } from "@/lib/models/bd-manifest";

export const runtime = "nodejs";

const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked");

type Format = "stl" | "glb";

const CONTENT_TYPE: Record<Format, string> = {
  // Match /api/export's STL content-type for consistency.
  stl: "application/sla",
  glb: "model/gltf-binary",
};

interface RouteContext {
  params: Promise<{ slug: string; preset: string }>;
}

export async function GET(req: NextRequest, ctx: RouteContext) {
  const { slug, preset } = await ctx.params;

  const format = req.nextUrl.searchParams.get("format") ?? "glb";
  if (format !== "stl" && format !== "glb") {
    return jsonError(400, `format must be "stl" or "glb", got "${format}"`);
  }

  // Allowlist: the model + preset must both be declared in the manifest.
  const model = await loadBdModel(slug);
  if (!model) return jsonError(404, `unknown build123d model: ${slug}`);
  if (!model.presets.some((p) => p.id === preset)) {
    return jsonError(404, `unknown preset "${preset}" for model "${slug}"`);
  }

  // Path is built only from allowlist-matched, registry-validated ids
  // (SAFE_ID_RE at bake time), so it cannot contain separators or dots.
  // The confinement check below is belt-and-suspenders.
  const abs = path.resolve(BAKED_ROOT, slug, `${preset}.${format}`);
  if (!abs.startsWith(BAKED_ROOT + path.sep)) {
    return jsonError(400, "resolved asset path escapes the baked root");
  }

  let bytes: Buffer;
  try {
    bytes = await fs.readFile(abs);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      // Manifest declares it but the bake didn't produce it — the build
      // step (BD_MODELS_ENABLED bake) didn't run or failed. Loud 404 so
      // the failure is visible rather than a silent empty viewer.
      return jsonError(
        404,
        `baked asset missing: ${slug}/${preset}.${format} — was the ` +
          `BD_MODELS_ENABLED preset bake run at build time?`,
      );
    }
    throw e;
  }

  // Copy into a fresh ArrayBuffer-backed view so the body is a plain
  // BodyInit carrying no unrelated heap.
  const body = new Uint8Array(bytes.byteLength);
  body.set(bytes);

  const headers: Record<string, string> = {
    "content-type": CONTENT_TYPE[format],
    "content-length": String(body.byteLength),
    // This URL (/api/bd-asset/<slug>/<preset>) is stable across deploys,
    // but the baked bytes behind it change whenever model geometry or a
    // preset value changes. It is NOT content-addressed (unlike /api/export's
    // HIT path, whose URL hashes the render), so `immutable` would let a
    // client serve last year's geometry after a redeploy. Allow shared
    // caching but require revalidation so a new bake is picked up promptly.
    "cache-control": "public, max-age=0, must-revalidate",
  };
  // STL is a download; GLB is fetched by the in-page viewer (inline).
  if (format === "stl") {
    headers["content-disposition"] =
      `attachment; filename="${slug}-${preset}.stl"`;
  }

  return new Response(body, { status: 200, headers });
}

function jsonError(status: number, error: string): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "content-type": "application/json" },
  });
}
