// Live build123d render endpoint — bead pst-6ugb (P2b of epic pst-7srz).
//
// The build123d analogue of /api/export, but with a fundamentally different
// shape: build123d is Python/OCP and CANNOT run in a Vercel function or in
// the browser, so there is NO WASM fallback. Every render goes to the
// bd-render Cloud Run service (P2a, services/bd-render/); a service failure
// is a clean 502, never a silent degrade to a second renderer.
//
//   POST /api/bd-render            body { slug, params }
//   POST /api/bd-render?format=stl same, STL bytes for download
//   POST /api/bd-render?format=3mf same, one-object multi-colour 3MF
//                                  (multiColour models only, else 400)
//
// Flow:
//   1. Gate: bdModelsEnabled() AND config present. Else 503 {disabled:true}
//      — the feature ships dark and a missing service config is not a crash.
//   2. Body shape + format check (400).
//   3. Manifest allowlist: unknown slug → 404.
//   4. JS manifest-RANGE pre-validation (unknown key / out-of-range → 400)
//      BEFORE the round-trip. The service re-validates authoritatively in
//      Python (registry.resolve_values); this is the fast local reject.
//   5. Content-addressed cache lookup (slug, normalized params, model
//      version, format). HIT → serve with x-cache=hit. build123d previews
//      hit this route on every manual refresh, so repeat combos MUST be
//      instant.
//   6. MISS → bd-render service. Success → cache + serve x-cache=miss.
//      Service 400 (the model rejected the values at build time, e.g. label
//      text below the stroke floor) → 400 with its message; any other
//      failure → 502 structured error (no fallback).
//
// No change to /api/export or its WASM fallback — this is a separate path.

import { type NextRequest } from "next/server";
import {
  CHARSET_RE,
  defaultsOf,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { bdModelsEnabled, loadBdModel, type BdParam } from "@/lib/models/bd-manifest";
import { downloadFilename } from "@/lib/models/download-name";
import {
  getBdRenderServiceConfig,
  renderBdViaService,
  type BdRenderFormat,
} from "@/lib/render-service/bd-client";
import {
  bdModelVersion,
  computeBdCacheKey,
  getBdRenderCacheStore,
  normalizeParams,
} from "@/lib/render-service/bd-cache";

export const runtime = "nodejs";
export const maxDuration = 120;

interface BdRenderBody {
  slug: string;
  params: Record<string, unknown>;
}

export async function POST(req: NextRequest) {
  // 1. Feature gate. Flag off OR no service config → clean 503, never a
  //    crash. Both conditions collapse to the same "not available" answer.
  const config = getBdRenderServiceConfig();
  if (!bdModelsEnabled() || !config) {
    return jsonError(503, "build123d live render is disabled", { disabled: true });
  }

  // 2. Format + body shape. Read the query off req.url (works for both a
  //    NextRequest and a plain Request, unlike req.nextUrl).
  const format = new URL(req.url).searchParams.get("format") ?? "glb";
  if (format !== "glb" && format !== "stl" && format !== "3mf") {
    return jsonError(400, `format must be "glb", "stl" or "3mf", got "${format}"`);
  }

  let body: BdRenderBody;
  try {
    body = (await req.json()) as BdRenderBody;
  } catch {
    return jsonError(400, "invalid JSON body");
  }
  if (typeof body?.slug !== "string") {
    return jsonError(400, "body.slug must be a string");
  }
  if (
    body.params !== undefined &&
    (typeof body.params !== "object" || body.params === null || Array.isArray(body.params))
  ) {
    return jsonError(400, "body.params must be an object");
  }
  const rawParams = body.params ?? {};

  // 3. Manifest allowlist. The manifest is the app's source of truth for
  //    which build123d models exist; an unknown slug never reaches the
  //    service.
  const model = await loadBdModel(body.slug);
  if (!model) {
    return jsonError(404, `unknown build123d model: ${body.slug}`);
  }
  if (format === "3mf" && !model.multiColour) {
    return jsonError(400, `${model.slug} is not a multi-colour model; 3mf is not available`);
  }

  // 4. JS manifest-range pre-check → fast 400 before the round-trip. The
  //    service still re-validates authoritatively (Python resolve_values).
  const validated = validateBdParams(model.params, rawParams);
  if ("error" in validated) {
    return jsonError(400, validated.error);
  }

  // 5. Content-addressed cache lookup.
  const store = getBdRenderCacheStore();
  let key: string | null = null;
  if (store) {
    try {
      key = computeBdCacheKey({
        slug: model.slug,
        normalizedParams: normalizeParams(validated.values),
        modelVersion: bdModelVersion(model),
        format,
      });
      const hit = await store.get(key, format);
      if (hit) {
        return bytesResponse(hit, downloadFilename(model.slug, model.params, validated.values, format), format, {
          cache: "HIT",
        });
      }
    } catch (e) {
      // A cache fault must never break a render — fall through to live.
      // key may be set (get failed) or null (key compute failed); the put
      // below skips when null.
      console.warn("bd-render cache lookup failed:", e);
    }
  }

  // 6. Live render via the service. No WASM fallback: any failure is a 502.
  const result = await renderBdViaService({
    config,
    slug: model.slug,
    params: validated.values,
    format,
    // Vercel delivers the OIDC token as a request header on each
    // invocation; VERCEL_OIDC_TOKEN covers `vercel env pull` local dev.
    vercelOidcToken:
      req.headers.get("x-vercel-oidc-token") ??
      process.env.VERCEL_OIDC_TOKEN ??
      null,
  });
  if (!result.ok) {
    // A service 400 is the model rejecting in-range values it cannot build
    // (label text below the stroke floor): relay its message to the user.
    if (result.badRequest !== undefined) {
      return jsonError(400, result.badRequest);
    }
    return jsonError(502, "bd-render service failed", { upstream: result.errorMessage });
  }

  const out = new Uint8Array(result.bytes.byteLength);
  out.set(result.bytes);
  if (store && key) {
    try {
      await store.put(key, format, out);
    } catch (e) {
      console.warn("bd-render cache write failed:", e);
    }
  }

  return bytesResponse(out, downloadFilename(model.slug, model.params, validated.values, format), format, {
    cache: store ? "MISS" : null,
    renderMs: result.renderMs,
  });
}

const CONTENT_TYPE: Record<BdRenderFormat, string> = {
  glb: "model/gltf-binary",
  stl: "application/sla",
  "3mf": "model/3mf",
};

// A HIT is content-addressed, so its bytes can never change for that (slug,
// params, model version, format) tuple — safe to mark immutable. A MISS
// keeps no-store: the same request will HIT next time and the fresh render
// carries the timing header.
function bytesResponse(
  bytes: Uint8Array,
  filename: string,
  format: BdRenderFormat,
  meta: { cache: "HIT" | "MISS" | null; renderMs?: number },
): Response {
  const body = new Uint8Array(bytes.byteLength);
  body.set(bytes);
  const headers: Record<string, string> = {
    "content-type": CONTENT_TYPE[format],
    "content-length": String(body.byteLength),
    "cache-control":
      meta.cache === "HIT"
        ? "public, max-age=31536000, immutable"
        : "no-store",
  };
  // STL/3MF are downloads; GLB is fetched inline by the in-page viewer. The name
  // carries any `filename`-flagged param's value (holder-spool-cradle-points
  // .stl) and must agree with BdDetailPage's a.download, which wins on the
  // fetch-blob path.
  if (format !== "glb") {
    headers["content-disposition"] = `attachment; filename="${filename}"`;
  }
  if (meta.cache) headers["x-cache"] = meta.cache;
  if (meta.renderMs !== undefined) headers["x-render-ms"] = meta.renderMs.toFixed(0);
  return new Response(body, { status: 200, headers });
}

interface BdValidated {
  values: Record<string, ParamValue>;
}
interface BdValidationError {
  error: string;
}

/**
 * Validate raw params against the manifest, filling defaults. Unlike the
 * SCAD export route's validateAndCoerce, this also enforces numeric min/max
 * from the manifest — build123d has no in-browser render to catch a bad
 * value, so the range check is the app's fast reject. Returns the FULL
 * resolved map (defaults included) so the cache key and the service build
 * agree on exactly one normalized param set.
 */
export function validateBdParams(
  manifest: BdParam[],
  raw: Record<string, unknown>,
): BdValidated | BdValidationError {
  const byName = new Map(manifest.map((p) => [p.name, p]));
  for (const key of Object.keys(raw)) {
    if (!byName.has(key)) return { error: `unknown param: ${key}` };
  }

  const out = defaultsOf(manifest);
  for (const [key, rawVal] of Object.entries(raw)) {
    const param = byName.get(key)!;
    const coerced = coerceBd(param, rawVal);
    if ("error" in coerced) return { error: coerced.error };
    out[key] = coerced.value;
  }
  return { values: out };
}

function coerceBd(
  param: BdParam,
  raw: unknown,
): { value: ParamValue } | { error: string } {
  switch (param.kind) {
    case "number":
    case "integer": {
      const n = typeof raw === "number" ? raw : Number(raw);
      if (!Number.isFinite(n)) {
        return { error: `param ${param.name}: not a finite number` };
      }
      const v = param.kind === "integer" ? Math.trunc(n) : n;
      if (param.min !== undefined && v < param.min) {
        return { error: `param ${param.name}: ${v} below min ${param.min}` };
      }
      if (param.max !== undefined && v > param.max) {
        return { error: `param ${param.name}: ${v} above max ${param.max}` };
      }
      return { value: v };
    }
    case "boolean":
      if (typeof raw === "boolean") return { value: raw };
      if (raw === "true") return { value: true };
      if (raw === "false") return { value: false };
      return { error: `param ${param.name}: invalid boolean value` };
    case "enum": {
      const s = String(raw);
      return param.choices.includes(s)
        ? { value: s }
        : { error: `param ${param.name}: ${s} not in ${param.choices.join("|")}` };
    }
    case "string": {
      // Mirrors registry._validate_text so a bad label is a fast 400; the
      // service still re-checks. Length counts code points, as Python does.
      const s = typeof raw === "string" ? raw : String(raw);
      const length = [...s].length;
      if (param.maxLength !== undefined && length > param.maxLength) {
        return { error: `${param.name}: ${length} characters > max length ${param.maxLength}` };
      }
      const charset = param.charset === undefined ? undefined : CHARSET_RE[param.charset];
      if (charset && !charset.test(s)) {
        const bad = [...s].find((ch) => !charset.test(ch));
        return { error: `${param.name}: character ${JSON.stringify(bad)} is not in charset ${param.charset}` };
      }
      return { value: s };
    }
  }
}

function jsonError(status: number, error: string, extra?: object): Response {
  return new Response(JSON.stringify({ error, ...extra }), {
    status,
    headers: { "content-type": "application/json" },
  });
}
