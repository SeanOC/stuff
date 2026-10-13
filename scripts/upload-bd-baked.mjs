#!/usr/bin/env node
// Upload the baked preset downloads to Vercel Blob (bead pst-scmib).
//
// Runs from scripts/bake-bd-presets.sh right after export.py, so only when
// BD_MODELS_ENABLED=1. The baked STL/3MF no longer fit in the Vercel
// function (pst-acoed), and rendering them on request blew bd-render's
// 90 s BD_RENDER_TIMEOUT for the tombstone sign's 3MF. So every
// advertised preset download is uploaded here at build time and
// /api/bd-asset streams it from the URL this script records.
//
// What is uploaded: for every manifest preset, <preset>.stl, plus
// <preset>.3mf when the model is multiColour — exactly the set
// /api/bd-asset serves. Per-colour STLs (<preset>-<part>.stl) are never
// uploaded: nothing serves them.
//
// Blob key: bd-baked/<VERCEL_ENV>/<sha256 of the bytes>/<slug>-<preset>.<fmt>
//   • the environment prefix keeps a preview bake out of production's
//     namespace (the token is shared by Production/Preview/Development);
//   • the content hash means a key never changes bytes: put() runs with
//     allowOverwrite:false and an existing key is accepted only when its
//     size matches. Unchanged geometry re-uses the old key (no per-deploy
//     re-upload, no storage growth), and an instant rollback still finds
//     every key its record names — nothing is ever deleted or replaced.
//   • the file name is the download name /api/bd-asset uses.
//
// The record (build123d/baked/blob-record.json, traced into the bd-asset
// function by next.config.mjs) maps "<slug>/<preset>.<fmt>" to the URL.
// It is the ONLY way the route finds a blob: request time cannot see
// VERCEL_GIT_COMMIT_SHA, and nothing is probed.
//
// Outside a Vercel build (no VERCEL_ENV: local dev, e2e) nothing is
// uploaded and no record is written; the route then reads the files from
// build123d/baked/ on disk. Either way a missing baked artefact fails the
// build. On Vercel a missing BLOB_READ_WRITE_TOKEN fails the build too: a
// skipped upload would ship pages whose downloads 404.

import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const RECORD_FILE = "blob-record.json";
const UPLOAD_CONCURRENCY = 6;

const CONTENT_TYPE = { stl: "application/sla", "3mf": "model/3mf" };

/** Every download /api/bd-asset serves from a bake: [{slug, preset, format}]. */
export function bakedDownloads(manifest) {
  return manifest.models.flatMap((model) =>
    model.presets.flatMap((preset) =>
      (model.multiColour ? ["stl", "3mf"] : ["stl"]).map((format) => ({
        slug: model.slug,
        preset: preset.id,
        format,
      })),
    ),
  );
}

export function recordKey({ slug, preset, format }) {
  return `${slug}/${preset}.${format}`;
}

export function blobPathname(env, sha256, { slug, preset, format }) {
  return `bd-baked/${env}/${sha256}/${slug}-${preset}.${format}`;
}

/** Read every baked download; throws listing ALL missing files. */
export function readBakedDownloads(manifest, bakedRoot) {
  const downloads = bakedDownloads(manifest);
  const missing = downloads
    .map(recordKey)
    .filter((key) => !fs.existsSync(path.join(bakedRoot, key)));
  if (missing.length > 0) {
    throw new Error(
      `upload-bd-baked: ${missing.length} baked download(s) missing under ` +
        `${bakedRoot}: ${missing.join(", ")}`,
    );
  }
  return downloads.map((d) => {
    const bytes = fs.readFileSync(path.join(bakedRoot, recordKey(d)));
    return { ...d, bytes, sha256: createHash("sha256").update(bytes).digest("hex") };
  });
}

/**
 * Upload every baked download through `store` and return the record.
 * store.head(pathname) → {url, size} | null; store.put(pathname, bytes,
 * contentType) → {url}, and must refuse to overwrite an existing key.
 */
export async function uploadBakedDownloads({ manifest, bakedRoot, env, commit, store }) {
  const files = readBakedDownloads(manifest, bakedRoot);
  const assets = {};
  let uploaded = 0;
  let queue = 0;
  const worker = async () => {
    while (queue < files.length) {
      const file = files[queue++];
      const pathname = blobPathname(env, file.sha256, file);
      let url;
      const existing = await store.head(pathname);
      if (existing) {
        if (existing.size !== file.bytes.byteLength) {
          throw new Error(
            `upload-bd-baked: ${pathname} exists with ${existing.size} bytes, ` +
              `expected ${file.bytes.byteLength} — refusing to serve it`,
          );
        }
        url = existing.url;
      } else {
        url = (await store.put(pathname, file.bytes, CONTENT_TYPE[file.format])).url;
        uploaded++;
      }
      assets[recordKey(file)] = {
        url,
        pathname,
        size: file.bytes.byteLength,
        sha256: file.sha256,
      };
    }
  };
  await Promise.all(Array.from({ length: UPLOAD_CONCURRENCY }, worker));
  const sorted = Object.fromEntries(Object.entries(assets).sort(([a], [b]) => a.localeCompare(b)));
  return {
    record: { schemaVersion: 1, env, commit: commit ?? null, assets: sorted },
    uploaded,
    reused: files.length - uploaded,
  };
}

/** The production store: Vercel Blob, public, never overwriting. */
export function vercelBlobStore(token) {
  return {
    async head(pathname) {
      const { head, BlobNotFoundError } = await import("@vercel/blob");
      try {
        const res = await head(pathname, { token });
        return { url: res.url, size: res.size };
      } catch (e) {
        if (e instanceof BlobNotFoundError) return null;
        throw e;
      }
    },
    async put(pathname, bytes, contentType) {
      const { put } = await import("@vercel/blob");
      return put(pathname, bytes, {
        access: "public",
        token,
        addRandomSuffix: false,
        allowOverwrite: false,
        contentType,
        // Content-addressed: the bytes behind a key never change.
        cacheControlMaxAge: 31536000,
      });
    },
  };
}

export async function main({ root, environ = process.env, store } = {}) {
  const manifest = JSON.parse(
    fs.readFileSync(path.join(root, "build123d", "manifest.json"), "utf8"),
  );
  const bakedRoot = path.join(root, "build123d", "baked");
  const recordPath = path.join(bakedRoot, RECORD_FILE);
  // Never let a previous run's record outlive this bake.
  fs.rmSync(recordPath, { force: true });

  const env = environ.VERCEL_ENV;
  if (!env) {
    const n = readBakedDownloads(manifest, bakedRoot).length;
    console.log(
      `upload-bd-baked: not a Vercel build (no VERCEL_ENV) — ${n} baked downloads ` +
        "stay on disk; /api/bd-asset serves build123d/baked/ directly.",
    );
    return null;
  }
  const token = environ.BLOB_READ_WRITE_TOKEN;
  if (!store && !token) {
    throw new Error(
      `upload-bd-baked: VERCEL_ENV=${env} but BLOB_READ_WRITE_TOKEN is not set — ` +
        "the baked STL/3MF downloads cannot be published (link the Blob store " +
        "to this environment, or unset BD_MODELS_ENABLED).",
    );
  }
  const { record, uploaded, reused } = await uploadBakedDownloads({
    manifest,
    bakedRoot,
    env,
    commit: environ.VERCEL_GIT_COMMIT_SHA,
    store: store ?? vercelBlobStore(token),
  });
  fs.writeFileSync(recordPath, JSON.stringify(record, null, 2) + "\n");
  console.log(
    `upload-bd-baked: ${uploaded} uploaded, ${reused} unchanged → ` +
      `${path.relative(root, recordPath)} (env ${env})`,
  );
  return record;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
  main({ root }).catch((e) => {
    console.error(e instanceof Error ? e.message : e);
    process.exit(1);
  });
}
