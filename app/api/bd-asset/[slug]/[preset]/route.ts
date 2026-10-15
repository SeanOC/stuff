// build123d baked-preset asset server (bead pst-0um9, epic pst-7srz).
//
// Serves the build-time-baked STL/GLB/3MF for one (model, preset) pair:
//   GET /api/bd-asset/<slug>/<preset>?format=glb   → viewer geometry
//   GET /api/bd-asset/<slug>/<preset>?format=stl   → print download
//   GET /api/bd-asset/<slug>/<preset>?format=3mf   → multi-colour print
//                                  download (multiColour models only)
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
//
// Only the baked GLBs ship in the Vercel function (pst-acoed: the
// STL/3MF/per-colour STLs pushed it past Vercel's 250 MB limit). On a
// Vercel build the bake publishes every preset STL (and 3MF, for
// multiColour models) to Vercel Blob and records the URLs in
// build123d/baked/blob-record.json (scripts/upload-bd-baked.mjs,
// pst-scmib); this route streams the recorded blob, same-origin, under
// the same headers as a disk read. Off Vercel (local dev, e2e) there is
// no record and the bake's files are read from disk. Nothing here
// renders on request: a preset download is ALWAYS a baked artefact, and
// a missing one is a loud 404. Non-preset parameter sets render through
// /api/bd-render (the detail page's download button for tweaked params).

import fs from "node:fs/promises";
import path from "node:path";
import { NextRequest } from "next/server";
import { loadBdManifest } from "@/lib/models/bd-manifest";
import { bakedBlobEntry } from "@/lib/models/bd-baked-record";

export const runtime = "nodejs";

const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked");

type Format = "stl" | "glb" | "3mf";

const CONTENT_TYPE: Record<Format, string> = {
  // Match /api/export's STL content-type for consistency.
  stl: "application/sla",
  glb: "model/gltf-binary",
  "3mf": "model/3mf",
};

interface RouteContext {
  params: Promise<{ slug: string; preset: string }>;
}

export async function GET(req: NextRequest, ctx: RouteContext) {
  const { slug, preset } = await ctx.params;

  const format = req.nextUrl.searchParams.get("format") ?? "glb";
  if (format !== "stl" && format !== "glb" && format !== "3mf") {
    return jsonError(400, `format must be "stl", "glb" or "3mf", got "${format}"`);
  }

  // Optional printer profile (pst-jyey1): the 3MF as that slicer's project,
  // baked as <preset>.<profile>.3mf. Allowlisted by the manifest like slugs.
  const profile = req.nextUrl.searchParams.get("profile") || null;
  if (profile && format !== "3mf") {
    return jsonError(400, "profile is only valid with format=3mf");
  }

  // Allowlist: the model + preset must both be declared in the manifest.
  const manifest = await loadBdManifest();
  if (profile && !manifest.printerProfiles.some((p) => p.id === profile)) {
    return jsonError(400, `unknown printer profile: ${profile}`);
  }
  const model = manifest.models.find((m) => m.slug === slug) ?? null;
  if (!model) return jsonError(404, `unknown build123d model: ${slug}`);
  const presetEntry = model.presets.find((p) => p.id === preset);
  if (!presetEntry) {
    return jsonError(404, `unknown preset "${preset}" for model "${slug}"`);
  }
  // Only multi-colour models bake a 3MF (scripts/export.py is_multi_colour
  // gate); say so rather than the misleading "bake didn't run" 404 below.
  if (format === "3mf" && !model.multiColour) {
    return jsonError(400, `${slug} is not a multi-colour model; 3mf is not available`);
  }

  // Path is built only from allowlist-matched, registry-validated ids
  // (SAFE_ID_RE at bake time), so it cannot contain separators or dots.
  // The confinement check below is belt-and-suspenders.
  const baked = profile ? `${preset}.${profile}.${format}` : `${preset}.${format}`;
  const abs = path.resolve(BAKED_ROOT, slug, baked);
  if (!abs.startsWith(BAKED_ROOT + path.sep)) {
    return jsonError(400, "resolved asset path escapes the baked root");
  }

  if (format !== "glb") {
    const entry = await bakedBlobEntry(BAKED_ROOT, slug, preset, format, profile ?? undefined);
    if (entry) {
      const upstream = await fetch(entry.url);
      if (!upstream.ok || !upstream.body) {
        return jsonError(
          502,
          `baked asset ${slug}/${baked} unavailable from the blob ` +
            `store (HTTP ${upstream.status})`,
        );
      }
      return new Response(upstream.body, {
        status: 200,
        headers: assetHeaders(slug, preset, format, entry.size, profile),
      });
    }
  }

  let bytes: Buffer;
  try {
    bytes = await fs.readFile(abs);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      // Manifest declares it but the bake didn't produce (or, on Vercel,
      // record) it — the BD_MODELS_ENABLED build step didn't run or
      // failed. Loud 404 so the failure is visible rather than a silent
      // empty viewer or a request-time render.
      return jsonError(
        404,
        `baked asset missing: ${slug}/${baked} — was the ` +
          `BD_MODELS_ENABLED preset bake run at build time?`,
      );
    }
    throw e;
  }

  // Copy into a fresh ArrayBuffer-backed view so the body is a plain
  // BodyInit carrying no unrelated heap.
  const body = new Uint8Array(bytes.byteLength);
  body.set(bytes);
  return new Response(body, {
    status: 200,
    headers: assetHeaders(slug, preset, format, body.byteLength, profile),
  });
}

function assetHeaders(
  slug: string,
  preset: string,
  format: Format,
  length: number,
  profile: string | null,
): Record<string, string> {
  const headers: Record<string, string> = {
    "content-type": CONTENT_TYPE[format],
    "content-length": String(length),
    // This URL (/api/bd-asset/<slug>/<preset>) is stable across deploys,
    // but the baked bytes behind it change whenever model geometry or a
    // preset value changes. It is NOT content-addressed (unlike /api/export's
    // HIT path, whose URL hashes the render), so `immutable` would let a
    // client serve last year's geometry after a redeploy. Allow shared
    // caching but require revalidation so a new bake is picked up promptly.
    "cache-control": "public, max-age=0, must-revalidate",
  };
  // STL/3MF are downloads; GLB is fetched by the in-page viewer (inline).
  // Baked assets are named by PRESET, not via downloadFilename's flagged
  // params: a preset id already names the variant, and once pst-026m4
  // consolidates presets the id IS the mount style — so this stays
  // `${slug}-${preset}.<format>` and never doubles the suffix. A printer
  // profile appends its id: `${slug}-${preset}-${profile}.3mf`.
  if (format !== "glb") {
    const stem = profile ? `${slug}-${preset}-${profile}` : `${slug}-${preset}`;
    headers["content-disposition"] = `attachment; filename="${stem}.${format}"`;
  }
  return headers;
}

function jsonError(status: number, error: string): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "content-type": "application/json" },
  });
}
