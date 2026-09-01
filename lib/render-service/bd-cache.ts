// Content-addressed cache for /api/bd-render — bead pst-6ugb (P2b).
//
// build123d previews are NOT rendered in the browser (OCP can't run there),
// so every manual "refresh" in BdDetailPage hits /api/bd-render over the
// network. Repeat param combos (a preset, a value the user toggled back to)
// must serve instantly instead of paying a Cloud Run round-trip each time —
// caching matters here in a way it does not for the in-browser WASM SCAD
// preview.
//
// Unlike lib/wasm/export-cache.ts, the key is NOT a SCAD closure-hash — a
// build123d model is Python, not a walkable include set. The key is:
//
//   key = sha256( slug + normalizedParams + modelVersion + format )
//
//   1. slug            — the manifest slug being built.
//   2. normalizedParams — every declared param with defaults resolved, keys
//                       sorted, values formatted stably (reused verbatim from
//                       export-cache so an omitted param and its explicit
//                       default collide to one entry).
//   3. modelVersion    — a digest of the model's manifest entry (params +
//                       presets) PLUS an operator renderer-version env, so a
//                       param-range edit OR a geometry-code bump busts the
//                       cache. See bdModelVersion.
//   4. format          — glb (preview bytes) and stl (download bytes) are
//                       DIFFERENT outputs for the same params, so they must
//                       never share an entry.
//
// Only successful (non-empty) renders are ever stored — the route enforces
// that, exactly as the SCAD export cache does.

import { createHash } from "node:crypto";
import type { BdModel } from "@/lib/models/bd-manifest";
import type { BdRenderFormat } from "./bd-client";

export { normalizeParams } from "@/lib/wasm/export-cache";

/**
 * Version component for a build123d model. Hashes the model's manifest
 * entry (the param definitions and presets — everything the manifest says
 * about how the model is parameterized) so any manifest change busts the
 * cache. A geometry change that leaves the params untouched is NOT visible
 * in the manifest, so BD_RENDER_SERVICE_RENDERER_VERSION is folded in too:
 * the operator bumps it in lockstep with the service image (same discipline
 * as export-cache's nativeRendererVersion), giving a manual bust lever.
 */
export function bdModelVersion(model: BdModel): string {
  const h = createHash("sha256");
  h.update("bd-model\0", "utf8");
  // params + presets are the manifest's full description of the model's
  // parameterization; title/blurb/category are display-only and can change
  // without affecting geometry, so they stay out of the version.
  h.update(JSON.stringify({ params: model.params, presets: model.presets }), "utf8");
  h.update("\0renderer:", "utf8");
  h.update(process.env.BD_RENDER_SERVICE_RENDERER_VERSION ?? "1", "utf8");
  return h.digest("hex");
}

/**
 * Compose the final content-addressed key. Each part is labeled so two
 * different components can never concatenate into the same byte stream.
 */
export function computeBdCacheKey(parts: {
  slug: string;
  normalizedParams: string;
  modelVersion: string;
  format: BdRenderFormat;
}): string {
  const h = createHash("sha256");
  h.update("slug:", "utf8");
  h.update(parts.slug, "utf8");
  h.update("\nparams:", "utf8");
  h.update(parts.normalizedParams, "utf8");
  h.update("\nmodel:", "utf8");
  h.update(parts.modelVersion, "utf8");
  h.update("\nformat:", "utf8");
  h.update(parts.format, "utf8");
  return h.digest("hex");
}

/**
 * Durable, cross-invocation store for rendered bytes. Behind an interface
 * so the route is testable with an in-memory fake; the production impl is
 * Vercel Blob (below). format is carried alongside the key because glb and
 * stl need distinct content-types on write.
 */
export interface BdRenderCacheStore {
  get(key: string, format: BdRenderFormat): Promise<Uint8Array | null>;
  put(key: string, format: BdRenderFormat, bytes: Uint8Array): Promise<void>;
}

const CONTENT_TYPE: Record<BdRenderFormat, string> = {
  glb: "model/gltf-binary",
  stl: "application/sla",
};

// Blob pathname namespace. key is a sha256 hex digest (unguessable,
// collision-free); the format suffix keeps glb/stl bytes at distinct paths.
function blobPathname(key: string, format: BdRenderFormat): string {
  return `bd-render-cache/${key}.${format}`;
}

/**
 * Vercel Blob-backed store. Returns null (caching off — every request pays
 * a live render) when no blob token is present, so local dev and CI without
 * Blob credentials keep working. Mirrors export-cache's store exactly, minus
 * the STL-only assumption.
 */
export function getBdRenderCacheStore(): BdRenderCacheStore | null {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return null;
  return {
    async get(key, format) {
      const { get } = await import("@vercel/blob");
      const res = await get(blobPathname(key, format), { access: "public", token });
      if (!res || !res.stream) return null;
      const buf = await new Response(res.stream).arrayBuffer();
      return new Uint8Array(buf);
    },
    async put(key, format, bytes) {
      const { put } = await import("@vercel/blob");
      await put(blobPathname(key, format), Buffer.from(bytes), {
        access: "public",
        token,
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: CONTENT_TYPE[format],
        cacheControlMaxAge: 31536000,
      });
    },
  };
}
