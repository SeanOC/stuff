// Lightweight listing used by the command palette's Models group
// (st-3lc). Returns just slug/title/stem/blurb — the palette doesn't
// need params or the full source, and shipping the whole discover
// payload would bloat the response.
//
// Kept out of layout.tsx so hydration isn't blocked on a filesystem
// scan. Palette fetches on first open.

import { NextResponse } from "next/server";
import { listModels } from "@/lib/models/discover";

export const dynamic = "force-static";

export async function GET() {
  const models = await listModels();
  return NextResponse.json({
    models: models.map((m) => ({
      slug: m.slug,
      title: m.title,
      stem: m.stem,
      blurb: m.blurb,
    })),
  });
}
