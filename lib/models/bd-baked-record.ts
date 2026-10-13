// The bake's Blob record (pst-scmib): where a Vercel build published each
// baked preset download. Written by scripts/upload-bd-baked.mjs into
// build123d/baked/blob-record.json and traced into the /api/bd-asset
// function (next.config.mjs). Absent off Vercel — the route then serves
// build123d/baked/ from disk.

import fs from "node:fs/promises";
import path from "node:path";

export const BLOB_RECORD_FILE = "blob-record.json";

export interface BakedBlobEntry {
  url: string;
  pathname: string;
  size: number;
  sha256: string;
}

interface BakedBlobRecord {
  schemaVersion: 1;
  env: string;
  commit: string | null;
  /** Keyed "<slug>/<preset>.<format>". */
  assets: Record<string, BakedBlobEntry>;
}

/** The recorded Blob entry for one baked download, or null when there is no record. */
export async function bakedBlobEntry(
  bakedRoot: string,
  slug: string,
  preset: string,
  format: string,
): Promise<BakedBlobEntry | null> {
  let raw: string;
  try {
    raw = await fs.readFile(path.join(bakedRoot, BLOB_RECORD_FILE), "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
  const record = JSON.parse(raw) as BakedBlobRecord;
  return record.assets[`${slug}/${preset}.${format}`] ?? null;
}
