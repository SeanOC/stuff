#!/usr/bin/env node
// Blob side of the content-addressed preset bake cache (bead pst-aqza2).
//
// scripts/bake-bd-presets.sh chains, in one cache DIR (a mktemp dir, never
// under build123d/baked/, so upload-bd-baked.mjs cannot publish a tarball):
//
//   export.py --cache-plan DIR/plan.json   keys + Blob pathname per preset
//   bd-bake-cache.mjs restore DIR          fetch hits → DIR/fetched/<key>.tar.gz
//   export.py --cache-dir DIR              extract hits, bake misses → DIR/store/
//   bd-bake-cache.mjs store DIR            upload the misses, print the summary
//
// Python owns keys, tarballs and their validation; this file only moves
// bytes. The key is a hash of the bake's INPUTS and carries no env prefix:
// a PR's preview bake serves production after merge. Tarballs are public
// (put() is access:"public") but derive only from committed sources, so the
// prefix is a cache, not a secret store.
//
// Correctness over speed: a lookup or fetch error is one log line and that
// preset bakes; a store error is a warning. Neither fails the build. Keys
// are never overwritten (head first, allowOverwrite:false, a size-matched
// race accepted) — upload-bd-baked.mjs's rules. Old keys are never pruned:
// the prefix grows by one tarball per preset whose inputs changed per build.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { vercelBlobStore } from "./upload-bd-baked.mjs";

const CONCURRENCY = 6;
const CONTENT_TYPE = "application/gzip";

async function eachLimited(items, fn) {
  let next = 0;
  const worker = async () => {
    while (next < items.length) await fn(items[next++]);
  };
  await Promise.all(Array.from({ length: CONCURRENCY }, worker));
}

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));

/** Fetch every planned preset's tarball that exists into dir/fetched/<key>.tar.gz. */
export async function restore({ dir, store, log = console.log }) {
  const started = performance.now();
  const { entries } = readJson(path.join(dir, "plan.json"));
  const fetchedDir = path.join(dir, "fetched");
  fs.mkdirSync(fetchedDir, { recursive: true });
  let fetched = 0;
  let bytes = 0;
  let errors = 0;
  await eachLimited(entries, async (entry) => {
    try {
      const body = await store.get(entry.pathname);
      if (!body) return;
      fs.writeFileSync(path.join(fetchedDir, `${entry.key}.tar.gz`), body);
      fetched++;
      bytes += body.byteLength;
    } catch (e) {
      errors++;
      log(`bake cache: ${entry.slug}/${entry.preset}: fetch failed (${e?.message ?? e}) — will bake`);
    }
  });
  const result = { planned: entries.length, fetched, bytes, errors,
    seconds: (performance.now() - started) / 1000 };
  fs.writeFileSync(path.join(dir, "restore.json"), JSON.stringify(result) + "\n");
  log(`bake cache: fetched ${fetched}/${entries.length} cached presets ` +
    `(${(bytes / 1e6).toFixed(1)} MB in ${result.seconds.toFixed(1)}s)`);
  return result;
}

/** Upload each preset the bake staged; never overwrite, never throw. */
export async function storeBaked({ dir, store, log = console.log }) {
  const started = performance.now();
  const bakeFile = path.join(dir, "bake.json");
  const staged = fs.existsSync(bakeFile) ? readJson(bakeFile).store : [];
  let stored = 0;
  let failed = 0;
  await eachLimited(staged, async ({ pathname, file }) => {
    try {
      const body = fs.readFileSync(path.join(dir, file));
      const existing = await store.head(pathname);
      if (existing) {
        if (existing.size !== body.byteLength) {
          failed++;
          log(`bake cache: WARN ${pathname} exists with ${existing.size} bytes, ` +
            `staged ${body.byteLength} — left as is`);
        }
        return;
      }
      try {
        await store.put(pathname, body, CONTENT_TYPE);
        stored++;
      } catch (e) {
        // A concurrent build baking the same inputs may have won the race.
        const raced = await store.head(pathname);
        if (!raced || raced.size !== body.byteLength) throw e;
      }
    } catch (e) {
      failed++;
      log(`bake cache: WARN store ${pathname} failed (${e?.message ?? e})`);
    }
  });
  return { staged: staged.length, stored, failed, seconds: (performance.now() - started) / 1000 };
}

/** The one-line summary: H hits, M misses, F MB fetched in Xs, bake Ys, store Zs. */
export function summary(dir, stored) {
  const read = (name) => {
    try {
      return readJson(path.join(dir, name));
    } catch {
      return null;
    }
  };
  const restored = read("restore.json") ?? { bytes: 0, seconds: 0 };
  const bake = read("bake.json") ?? { hits: 0, misses: 0, bakeSeconds: 0 };
  return (
    `bake cache: ${bake.hits} hits, ${bake.misses} misses, ` +
    `${(restored.bytes / 1e6).toFixed(1)} MB fetched in ${restored.seconds.toFixed(1)}s, ` +
    `bake ${bake.bakeSeconds.toFixed(1)}s, store ${stored.seconds.toFixed(1)}s ` +
    `(${stored.stored} stored, ${stored.failed} store failures)`
  );
}

export async function main({ argv = process.argv.slice(2), environ = process.env, store, log = console.log } = {}) {
  const [command, dir] = argv;
  if (!["restore", "store"].includes(command) || !dir) {
    throw new Error("usage: bd-bake-cache.mjs restore|store DIR");
  }
  const token = environ.BLOB_READ_WRITE_TOKEN;
  if (!store && !token) throw new Error("bd-bake-cache: BLOB_READ_WRITE_TOKEN is not set");
  store ??= vercelBlobStore(token);
  if (command === "restore") return restore({ dir, store, log });
  const stored = await storeBaked({ dir, store, log });
  log(summary(dir, stored));
  return stored;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  // Never fails the build: the shell falls back to a full bake on a failed
  // restore, and a failed store only costs the next build a re-bake.
  main().catch((e) => {
    console.log(`bake cache: ${process.argv[2] ?? "?"} failed (${e instanceof Error ? e.message : e})`);
    process.exit(1);
  });
}
