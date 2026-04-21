// Serves a model's iso-view thumbnail from `renders/<stem>/iso.png`.
// Returns 404 if the file isn't there — the gallery shows a blank tile
// in that case (no need for a server-side placeholder).
//
// Thumbnails are produced by the scad-render skill; we don't generate
// them on demand here. If you want fresh thumbs, run that skill.

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";
import { slugToStem } from "@/lib/models/discover";

const RENDERS_ROOT = path.resolve(process.cwd(), "renders");
const SAFE_STEM_RE = /^[A-Za-z0-9_]+$/;

export async function GET(req: NextRequest) {
  const slug = req.nextUrl.searchParams.get("model");
  if (!slug) return new Response("missing model", { status: 400 });

  const stem = slugToStem(slug);
  if (!SAFE_STEM_RE.test(stem)) {
    return new Response("invalid model slug", { status: 403 });
  }

  const abs = path.join(RENDERS_ROOT, stem, "iso.png");
  try {
    const data = await fs.readFile(abs);
    return new Response(new Uint8Array(data), {
      status: 200,
      headers: {
        "content-type": "image/png",
        "cache-control": "public, max-age=300",
      },
    });
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return new Response("no thumbnail", { status: 404 });
    }
    throw e;
  }
}
