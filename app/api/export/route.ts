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
import {
  computeCacheKey,
  computeClosureHash,
  getExportCacheStore,
  normalizeParams,
  rendererVersion,
} from "@/lib/wasm/export-cache";

export const runtime = "nodejs";
export const maxDuration = 120;

const REPO_ROOT = process.cwd();
const LIBS_ROOT = path.resolve(REPO_ROOT, "libs");
const MODELS_ROOT = path.resolve(REPO_ROOT, "models");
const FIXTURES_ROOT = path.resolve(REPO_ROOT, "tests/fixtures");
// Two roots: real user models under models/, plus a narrow allowance
// for e2e fixtures under tests/fixtures/. Fixtures stay out of the
// gallery but are render-callable so bug-regression.spec.ts can
// exercise the same export path users hit.
const MODEL_PATH_RE = /^(?:models|tests\/fixtures)\/[A-Za-z0-9._/-]+\.scad$/;

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
  if (
    !abs.startsWith(MODELS_ROOT + path.sep) &&
    !abs.startsWith(FIXTURES_ROOT + path.sep)
  ) {
    return jsonError(403, "model path escapes allowed roots");
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

  const filename = path.basename(body.model, ".scad") + ".stl";
  const fetchLibFile = fsLibFetcher;
  const fetchAssetFile = assetFetcherFor(path.dirname(abs));

  // Content-addressed cache lookup. The key hashes the model's full render
  // closure (original source + libs + import()ed assets), the fully-resolved
  // params, and the renderer version — so a hit is guaranteed byte-identical
  // to what a fresh render would produce. A HIT skips the ~22s render.
  const store = getExportCacheStore();
  let cacheKey: string | null = null;
  if (store) {
    try {
      cacheKey = computeCacheKey({
        closureHash: await computeClosureHash({
          entrySource: source,
          fetchLibFile,
          fetchAssetFile,
        }),
        normalizedParams: normalizeParams(validated.values),
        rendererVersion: rendererVersion(),
      });
      const hit = await store.get(cacheKey);
      if (hit) return stlResponse(hit, filename, { cache: "HIT" });
    } catch (e) {
      // A cache fault must never break exports — fall through to a live
      // render. cacheKey may be set (store.get failed) or null (hashing
      // failed); either way we skip the store.put below when it's null.
      console.warn("export cache lookup failed:", e);
    }
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
    fetchLibFile,
    fetchAssetFile,
  });
  if (!result.ok || !result.stl) {
    return jsonError(500, "render failed", {
      message: result.errorMessage ?? "unknown",
      stderrTail: result.stderr.slice(-12),
      missing: result.missing,
    });
  }

  // STL is binary; copy into a tight ArrayBuffer so the Response body
  // doesn't drag along any unrelated WASM heap.
  const out = new Uint8Array(result.stl.byteLength);
  out.set(result.stl);

  // Cache ONLY this verified-good render. store/cacheKey are both set only
  // when caching is configured AND the key was computed cleanly above. A put
  // failure is best-effort — never fail the export because the cache write
  // stumbled.
  if (store && cacheKey) {
    try {
      await store.put(cacheKey, out);
    } catch (e) {
      console.warn("export cache write failed:", e);
    }
  }

  return stlResponse(out, filename, {
    // Only label a MISS when caching is actually in play; with no store the
    // response carries no x-cache signal at all (today's behavior).
    cache: store ? "MISS" : null,
    renderMs: result.wallMs,
    libsMounted: result.filesMounted,
  });
}

// A HIT is content-addressed, so it's safe to mark immutable — the URL's
// bytes can never change for that (model, params, renderer) triple. A MISS
// keeps no-store: the same request will HIT next time and the fresh render
// carries the diagnostic timing headers.
function stlResponse(
  bytes: Uint8Array,
  filename: string,
  meta: { cache: "HIT" | "MISS" | null; renderMs?: number; libsMounted?: number },
): Response {
  // Copy into a fresh ArrayBuffer-backed view so the body is a plain
  // BodyInit (not SharedArrayBuffer-backed) and carries no unrelated heap.
  const body = new Uint8Array(bytes.byteLength);
  body.set(bytes);
  const headers: Record<string, string> = {
    "content-type": "application/sla",
    "content-length": String(body.byteLength),
    "content-disposition": `attachment; filename="${filename}"`,
    "cache-control":
      meta.cache === "HIT"
        ? "public, max-age=31536000, immutable"
        : "no-store",
  };
  if (meta.cache) headers["x-cache"] = meta.cache;
  if (meta.renderMs !== undefined) headers["x-render-ms"] = meta.renderMs.toFixed(0);
  if (meta.libsMounted !== undefined) headers["x-libs-mounted"] = String(meta.libsMounted);
  return new Response(body, { status: 200, headers });
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

// Binary import() assets (STL meshes) resolve relative to the model
// file's own directory — the same rule OpenSCAD applies to import()
// paths. Confined to the two allowed model roots. st-zph: this fetcher
// was missing entirely, so import()-based models exported without
// their mesh — renderToStl now fails hard on that, and this supplies
// the asset so it doesn't.
function assetFetcherFor(modelDir: string) {
  return async (relPath: string): Promise<Uint8Array | null> => {
    const normalized = path.normalize(relPath);
    if (normalized.startsWith("..") || path.isAbsolute(normalized)) return null;
    const abs = path.resolve(modelDir, normalized);
    if (
      !abs.startsWith(MODELS_ROOT + path.sep) &&
      !abs.startsWith(FIXTURES_ROOT + path.sep)
    ) {
      return null;
    }
    try {
      return new Uint8Array(await fs.readFile(abs));
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
      throw e;
    }
  };
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
