// Content-addressed cache for /api/export renders.
//
// /api/export live-renders via openscad-wasm on every request; hull-heavy
// models (the Ego blower mount) take ~22s even warm, risking cold-start
// 504s. This module keys each successful render by content so an identical
// request is served from a durable blob store in sub-second time, while any
// change to the model, its libraries, the params, or the renderer forces a
// fresh render.
//
// The cache key is composite and fully content-addressed (st-uqk):
//
//   key = sha256( closureHash + normalizedParams + rendererVersion )
//
//   1. closureHash    — sha256 of the entry .scad PLUS every file in its
//                       include/use closure and every import()ed asset. Any
//                       edit to the model or a shared lib it pulls in changes
//                       the hash (the "account for model updates" rule). We
//                       hash CONTENT, never mtime/version strings, because
//                       those are unreliable in serverless/build.
//   2. normalizedParams — every declared param with defaults resolved, keys
//                       sorted, stable value formatting. An omitted param and
//                       its explicit default collide to the same string;
//                       param order never matters; any value change differs.
//   3. rendererVersion — the openscad-wasm-prebuilt pin. A renderer upgrade
//                       can change output, so it must bust the cache.
//
// Only successful renders are ever stored (see the route): a failed/partial
// render must never be cached (that was the whole st-zph/st-7x7 class).

import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import {
  buildIncludeClosure,
  type AssetFetcher,
  type FileFetcher,
} from "./closure";
import type { ParamValue } from "@/lib/scad-params/parse";

/**
 * SHA-256 over the full render closure: the entry source, every resolved
 * include/use file, and every import()ed binary asset. Files and assets are
 * sorted by path first so the digest is independent of include-walk order —
 * only the SET and CONTENTS of the closure matter, not the traversal.
 */
export async function computeClosureHash(opts: {
  entrySource: string;
  fetchLibFile: FileFetcher;
  fetchAssetFile?: AssetFetcher;
}): Promise<string> {
  const closure = await buildIncludeClosure({
    entrySource: opts.entrySource,
    fetchLibFile: opts.fetchLibFile,
    fetchAssetFile: opts.fetchAssetFile,
  });

  const h = createHash("sha256");
  h.update("entry\0");
  h.update(opts.entrySource, "utf8");
  h.update("\0");

  const files = [...closure.files].sort((a, b) =>
    a.fsPath < b.fsPath ? -1 : a.fsPath > b.fsPath ? 1 : 0,
  );
  for (const f of files) {
    h.update("file\0");
    h.update(f.fsPath, "utf8");
    h.update("\0");
    h.update(f.source, "utf8");
    h.update("\0");
  }

  const assets = [...closure.assets].sort((a, b) =>
    a.fsPath < b.fsPath ? -1 : a.fsPath > b.fsPath ? 1 : 0,
  );
  for (const a of assets) {
    h.update("asset\0");
    h.update(a.fsPath, "utf8");
    h.update("\0");
    h.update(a.data);
    h.update("\0");
  }

  return h.digest("hex");
}

/**
 * Canonical string for a fully-resolved param map. Callers must pass a map
 * that already contains EVERY declared param with defaults filled in (the
 * export route's `validateAndCoerce` does this via `defaultsOf`), so an
 * omitted param and its explicit default produce identical output. Keys are
 * sorted and each value formatted stably.
 */
export function normalizeParams(values: Record<string, ParamValue>): string {
  const keys = Object.keys(values).sort();
  const parts = keys.map(
    (k) => JSON.stringify(k) + ":" + canonicalValue(values[k]),
  );
  return "{" + parts.join(",") + "}";
}

function canonicalValue(v: ParamValue): string {
  // Collapse -0 to 0 so a sign that OpenSCAD can't distinguish never splits
  // the cache. Strings and booleans round-trip through JSON unchanged.
  if (typeof v === "number") return Object.is(v, -0) ? "0" : String(v);
  return JSON.stringify(v);
}

/**
 * Compose the final content-addressed key. Deliberately labels each part so
 * two different components can never concatenate into the same byte stream.
 */
export function computeCacheKey(parts: {
  closureHash: string;
  normalizedParams: string;
  rendererVersion: string;
}): string {
  const h = createHash("sha256");
  h.update("closure:", "utf8");
  h.update(parts.closureHash, "utf8");
  h.update("\nparams:", "utf8");
  h.update(parts.normalizedParams, "utf8");
  h.update("\nrenderer:", "utf8");
  h.update(parts.rendererVersion, "utf8");
  return h.digest("hex");
}

let cachedRendererVersion: string | null = null;

/**
 * The pinned openscad-wasm-prebuilt version. Read from the repo package.json
 * (the pin is exact, so it matches the installed build) rather than the
 * package's own package.json, whose `exports` map blocks deep imports.
 */
export function rendererVersion(): string {
  if (cachedRendererVersion !== null) return cachedRendererVersion;
  try {
    const pkgPath = path.resolve(process.cwd(), "package.json");
    const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8")) as {
      dependencies?: Record<string, string>;
    };
    cachedRendererVersion =
      pkg.dependencies?.["openscad-wasm-prebuilt"] ?? "unknown";
  } catch {
    cachedRendererVersion = "unknown";
  }
  return cachedRendererVersion;
}

/**
 * Renderer-version component for the NATIVE render service path (st-d32).
 * Native OpenSCAD and openscad-wasm tessellate differently, so their
 * outputs must never share a cache entry: the "native:" prefix guarantees
 * this can never collide with rendererVersion() above (a bare semver).
 *
 * The suffix comes from RENDER_SERVICE_RENDERER_VERSION — the operator
 * bumps it in lockstep with the service image's openscad pin
 * (services/render/Dockerfile base tag) so a renderer upgrade busts the
 * cache, exactly like the WASM pin does.
 */
export function nativeRendererVersion(): string {
  return "native:" + (process.env.RENDER_SERVICE_RENDERER_VERSION ?? "1");
}

/**
 * Durable, cross-invocation store for rendered STL bytes. Kept behind an
 * interface so the route logic is testable with an in-memory fake — the
 * production impl is Vercel Blob (below).
 */
export interface ExportCacheStore {
  get(key: string): Promise<Uint8Array | null>;
  put(key: string, bytes: Uint8Array): Promise<void>;
}

// Blob pathname namespace. The key is a sha256 hex digest, so the path is
// unguessable and collision-free.
function blobPathname(key: string): string {
  return `export-cache/${key}.stl`;
}

/**
 * Vercel Blob-backed store. Returns null (caching disabled, falls back to
 * live render every time — today's behavior) when no blob token is present,
 * so local dev and CI without Blob credentials keep working unchanged.
 *
 * Storage note: Blob has no auto-eviction, so the namespace grows unbounded.
 * That is acceptable short-term for a content-addressed cache (dead keys are
 * simply never read again); a TTL/LRU sweep can come later. cacheControlMaxAge
 * is set long so hits also ride Vercel's edge/browser cache.
 */
export function getExportCacheStore(): ExportCacheStore | null {
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return null;
  return {
    async get(key) {
      const { get } = await import("@vercel/blob");
      const res = await get(blobPathname(key), { access: "public", token });
      if (!res || !res.stream) return null;
      const buf = await new Response(res.stream).arrayBuffer();
      return new Uint8Array(buf);
    },
    async put(key, bytes) {
      const { put } = await import("@vercel/blob");
      // Byte-identical content re-put under the same key on a thundering-herd
      // miss — allowOverwrite keeps that from throwing. Buffer.from wraps the
      // view without copying and satisfies the SDK's PutBody type.
      await put(blobPathname(key), Buffer.from(bytes), {
        access: "public",
        token,
        addRandomSuffix: false,
        allowOverwrite: true,
        contentType: "application/sla",
        cacheControlMaxAge: 31536000,
      });
    },
  };
}
