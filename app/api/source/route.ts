// Read-only endpoint that serves SCAD source files from the repo's
// `libs/` and `models/` directories to the browser. The WASM render
// driver fetches its include closure via this route.
//
// Path safety: only paths matching `^(libs|models)/[A-Za-z0-9._/-]+$`
// are accepted, and the resolved absolute path must still live under
// the repo root. Symlinks ARE followed (libs/BOSL2 etc. are symlinks
// into a sibling clone — see CLAUDE.md).

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";

const REPO_ROOT = process.cwd();
const ALLOWED_RE = /^(libs|models)\/[A-Za-z0-9._/-]+\.scad$/;

export async function GET(req: NextRequest) {
  const reqPath = req.nextUrl.searchParams.get("path");
  if (!reqPath) {
    return new Response("missing path", { status: 400 });
  }
  if (!ALLOWED_RE.test(reqPath)) {
    return new Response("path not allowed", { status: 403 });
  }

  // Resolve and double-check confinement, defending against `..`
  // segments slipping past the regex.
  const abs = path.resolve(REPO_ROOT, reqPath);
  if (!abs.startsWith(REPO_ROOT + path.sep)) {
    return new Response("path escapes root", { status: 403 });
  }

  let source: string;
  try {
    source = await fs.readFile(abs, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return new Response("not found", { status: 404 });
    }
    throw e;
  }
  return new Response(source, {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=60",
    },
  });
}
