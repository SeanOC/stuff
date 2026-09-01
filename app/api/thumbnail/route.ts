// Serves a model's gallery thumbnail. Two sources, one URL:
//
//   • SCAD models      → renders/<stem>/iso.png, produced by the
//                        scad-render skill / scripts/render-all.py.
//   • build123d models → build123d/baked/<slug>/<first-preset>.png,
//                        rendered by the SAME build-time bake that emits
//                        the detail view's GLB + STL (scripts/bake-bd-
//                        presets.sh → export.py --presets-only). So a
//                        model or preset change can never leave the card
//                        showing stale geometry (bead pst-1vi5).
//
// Returns 404 if neither source has the file — the gallery shows a blank
// tile in that case (no server-side placeholder). For a build123d model
// a 404 means the BD_MODELS_ENABLED preset bake didn't run this build,
// exactly like /api/bd-asset's missing-asset 404.

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";
import { slugToStem } from "@/lib/models/discover";
import { bdModelsEnabled, loadBdModel } from "@/lib/models/bd-manifest";

export const runtime = "nodejs";

const RENDERS_ROOT = path.resolve(process.cwd(), "renders");
const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked");
const SAFE_STEM_RE = /^[A-Za-z0-9_]+$/;

export async function GET(req: NextRequest) {
  const slug = req.nextUrl.searchParams.get("model");
  if (!slug) return new Response("missing model", { status: 400 });

  const stem = slugToStem(slug);
  if (!SAFE_STEM_RE.test(stem)) {
    return new Response("invalid model slug", { status: 403 });
  }

  // 1. SCAD renders convention. This is the fast path for every .scad
  //    model; a hit returns before the manifest is ever read.
  const rendered = await readPng(path.join(RENDERS_ROOT, stem, "iso.png"));
  if (rendered) {
    return pngResponse(rendered, "public, max-age=300");
  }

  // 2. build123d baked thumbnail — single source of truth with the GLB.
  //    Allowlist: only a slug the manifest declares reaches the disk,
  //    and the resolved path is confined under BAKED_ROOT.
  if (bdModelsEnabled()) {
    const model = await loadBdModel(slug);
    const presetId = model?.presets[0]?.id;
    if (model && presetId) {
      const abs = path.resolve(BAKED_ROOT, slug, `${presetId}.png`);
      if (abs.startsWith(BAKED_ROOT + path.sep)) {
        // Stable URL, bytes change per bake (like /api/bd-asset): allow
        // shared caching but require revalidation so a redeploy's fresh
        // thumbnail is picked up promptly rather than served stale.
        const baked = await readPng(abs);
        if (baked) {
          return pngResponse(baked, "public, max-age=0, must-revalidate");
        }
      }
    }
  }

  return new Response("no thumbnail", { status: 404 });
}

/** Read a PNG, or null on ENOENT. Other errors propagate. */
async function readPng(abs: string): Promise<Buffer | null> {
  try {
    return await fs.readFile(abs);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
}

function pngResponse(data: Buffer, cacheControl: string): Response {
  return new Response(new Uint8Array(data), {
    status: 200,
    headers: {
      "content-type": "image/png",
      "cache-control": cacheControl,
    },
  });
}
