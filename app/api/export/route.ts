// Server-side STL export endpoint.
//
// Reuses lib/wasm/render.ts (openscad-wasm-prebuilt + Manifold backend)
// rather than shelling out to a native binary — keeps one rendering
// codepath and avoids packaging a Linux openscad in the function bundle
// (~50MB after compression). The same closure walker mounts only the
// include set the model needs, so cold renders stay bounded.
//
// Validation layers (in order):
//   1. Path regex: `^models/[A-Za-z0-9._/-]+\.scad$`
//   2. Path-resolve confinement under <repo>/models
//   3. Body shape (model:string, params:object)
//   4. Every param key must exist in the parsed @param manifest
//   5. Every param value must match its declared kind (and enum choices)
//
// Anything that fails 1-2 returns 403; 3-5 return 400. WASM render
// failures bubble up as 500 with the openscad stderr tail.
//
// Runtime: Fluid Compute Node.js. maxDuration bumped to 120s to give
// CSG-heavy models headroom (default 300s on Vercel as of 2026).

import fs from "node:fs/promises";
import path from "node:path";
import { type NextRequest } from "next/server";
import {
  applyParamOverrides,
  defaultsOf,
  parseScadParams,
  type Param,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";

export const runtime = "nodejs";
export const maxDuration = 120;

const REPO_ROOT = process.cwd();
const LIBS_ROOT = path.resolve(REPO_ROOT, "libs");
const MODELS_ROOT = path.resolve(REPO_ROOT, "models");
const MODEL_PATH_RE = /^models\/[A-Za-z0-9._/-]+\.scad$/;

interface ExportBody {
  model: string;
  params: Record<string, unknown>;
}

export async function POST(req: NextRequest) {
  let body: ExportBody;
  try {
    body = (await req.json()) as ExportBody;
  } catch {
    return jsonError(400, "invalid JSON body");
  }
  if (typeof body?.model !== "string") {
    return jsonError(400, "body.model must be a string");
  }
  if (body.params !== undefined && (typeof body.params !== "object" || Array.isArray(body.params))) {
    return jsonError(400, "body.params must be an object");
  }

  if (!MODEL_PATH_RE.test(body.model)) {
    return jsonError(403, "model path not allowed");
  }
  const abs = path.resolve(REPO_ROOT, body.model);
  if (!abs.startsWith(MODELS_ROOT + path.sep)) {
    return jsonError(403, "model path escapes models/");
  }

  let source: string;
  try {
    source = await fs.readFile(abs, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return jsonError(404, "model not found");
    }
    throw e;
  }

  const { params: manifest } = parseScadParams(source);
  const validated = validateAndCoerce(manifest, body.params ?? {});
  if ("error" in validated) {
    return jsonError(400, validated.error);
  }

  // Rewrite each @param's own assignment line in-source. We cannot use
  // `-D` because openscad-wasm-prebuilt silently ignores command-line
  // defines; and we cannot prepend a prelude because OpenSCAD's last-
  // assignment-wins scoping would let the file's own defaults clobber
  // the override. Mutating the assignment line is the only path that
  // sticks under WASM.
  const sourceWithOverrides = applyParamOverrides(source, manifest, validated.values);

  const result = await renderToStl({
    source: sourceWithOverrides,
    fetchLibFile: fsLibFetcher,
  });
  if (!result.ok || !result.stl) {
    return jsonError(500, "render failed", {
      message: result.errorMessage ?? "unknown",
      stderrTail: result.stderr.slice(-12),
      missing: result.missing,
    });
  }

  const filename = path.basename(body.model, ".scad") + ".stl";
  // STL is binary; copy into a tight ArrayBuffer so the Response body
  // doesn't drag along any unrelated WASM heap.
  const out = new Uint8Array(result.stl.byteLength);
  out.set(result.stl);
  return new Response(out, {
    status: 200,
    headers: {
      "content-type": "application/sla",
      "content-length": String(out.byteLength),
      "content-disposition": `attachment; filename="${filename}"`,
      "x-render-ms": result.wallMs.toFixed(0),
      "x-libs-mounted": String(result.filesMounted),
      "cache-control": "no-store",
    },
  });
}

interface ValidatedParams { values: Record<string, ParamValue> }
interface ValidationError { error: string }

function validateAndCoerce(
  manifest: Param[],
  raw: Record<string, unknown>,
): ValidatedParams | ValidationError {
  const byName = new Map(manifest.map((p) => [p.name, p]));
  for (const key of Object.keys(raw)) {
    if (!byName.has(key)) return { error: `unknown param: ${key}` };
  }

  const out = defaultsOf(manifest);
  for (const [key, rawVal] of Object.entries(raw)) {
    const param = byName.get(key)!;
    const coerced = coerce(param, rawVal);
    if (coerced === null) {
      return { error: `param ${key}: invalid ${param.kind} value` };
    }
    out[key] = coerced;
  }
  return { values: out };
}

function coerce(param: Param, raw: unknown): ParamValue | null {
  switch (param.kind) {
    case "number":
    case "integer": {
      const n = typeof raw === "number" ? raw : Number(raw);
      if (!Number.isFinite(n)) return null;
      return param.kind === "integer" ? Math.trunc(n) : n;
    }
    case "boolean":
      if (typeof raw === "boolean") return raw;
      if (raw === "true") return true;
      if (raw === "false") return false;
      return null;
    case "enum": {
      const s = String(raw);
      return param.choices.includes(s) ? s : null;
    }
    case "string":
      return typeof raw === "string" ? raw : String(raw);
  }
}

async function fsLibFetcher(relPath: string): Promise<string | null> {
  // relPath comes from include/use directives like "BOSL2/std.scad".
  const normalized = path.normalize(relPath);
  if (normalized.startsWith("..") || path.isAbsolute(normalized)) return null;
  const abs = path.resolve(LIBS_ROOT, normalized);
  if (!abs.startsWith(LIBS_ROOT + path.sep)) return null;
  try {
    return await fs.readFile(abs, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
}

function jsonError(status: number, error: string, extra?: object): Response {
  return new Response(JSON.stringify({ error, ...extra }), {
    status,
    headers: { "content-type": "application/json" },
  });
}
