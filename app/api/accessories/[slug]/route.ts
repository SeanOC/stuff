// Streams an accessory STL from `accessories/<slug>.stl` with a
// download disposition. We don't use Next.js's `public/` static
// serving because this codebase routes every binary asset through API
// handlers with `outputFileTracingIncludes` (see next.config.mjs) —
// keeping that convention so accessories ship with the function bundle
// on Vercel and don't pollute `public/`.

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";
import { getAccessoryBySlug } from "@/lib/accessories/discover";

const REPO_ROOT = process.cwd();
const ACCESSORIES_ROOT = path.resolve(REPO_ROOT, "accessories");

interface RouteContext {
  params: Promise<{ slug: string }>;
}

export async function GET(_req: NextRequest, ctx: RouteContext) {
  const { slug } = await ctx.params;
  const entry = await getAccessoryBySlug(slug);
  if (!entry) return new Response("not found", { status: 404 });

  // Re-confine the catalog-supplied path under accessories/ even though
  // discover.ts already validated the slug — defense in depth against a
  // future catalog edit that points stlPath at a traversal-y location.
  const abs = path.resolve(REPO_ROOT, entry.stlPath);
  if (!abs.startsWith(ACCESSORIES_ROOT + path.sep)) {
    return new Response("path escapes accessories root", { status: 403 });
  }

  let data: Buffer;
  try {
    data = await fs.readFile(abs);
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return new Response("file missing", { status: 404 });
    }
    throw e;
  }

  const filename = `${entry.slug}.stl`;
  return new Response(new Uint8Array(data), {
    status: 200,
    headers: {
      "content-type": "application/sla",
      "content-length": String(data.byteLength),
      "content-disposition": `attachment; filename="${filename}"`,
      "cache-control": "public, max-age=300",
    },
  });
}
