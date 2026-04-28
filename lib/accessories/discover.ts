// Filesystem-backed accessory discovery. Mirrors lib/models/discover.ts
// but for the static-STL accessory catalog. Server-only — these helpers
// hit the disk to verify each catalog entry's STL exists and to read
// its size for the UI.
//
// Static-file serving: the codebase has no `public/` directory and
// instead routes all binary assets through API handlers with
// `outputFileTracingIncludes` (see next.config.mjs). Following that
// convention, accessory STLs live at `accessories/<slug>.stl` on disk
// and are served via `app/api/accessories/[slug]/route.ts`. The
// `downloadUrl` returned here points at that route.
//
// `fileSize` is computed eagerly on every list call. With <50
// accessories that's a cheap stat per request; if the catalog ever
// grows we can memoize against mtime.

import fs from "node:fs/promises";
import path from "node:path";
import { ACCESSORIES, type AccessoryCatalogEntry } from "./catalog";

const REPO_ROOT = process.cwd();
const SAFE_SLUG_RE = /^[A-Za-z0-9_-]+$/;

export interface AccessoryEntry extends AccessoryCatalogEntry {
  /** URL the browser should hit to download the STL. */
  downloadUrl: string;
  /** Bytes on disk. Useful for "16.4 MB" labels in the UI. */
  fileSize: number;
}

/**
 * List every accessory in the catalog whose STL resolves on disk.
 *
 * Catalog entries pointing at a missing file are dropped from the
 * returned list and a warning is logged — that way the gallery and
 * model pages keep rendering even when someone forgets to commit the
 * STL alongside the catalog edit. The on-disk requirement is asserted
 * by the test suite, so the warning surfaces in CI.
 */
export async function listAccessories(): Promise<AccessoryEntry[]> {
  const out: AccessoryEntry[] = [];
  for (const entry of ACCESSORIES) {
    if (!SAFE_SLUG_RE.test(entry.slug)) {
      console.warn(
        `[accessories] skipping "${entry.slug}": slug must match ${SAFE_SLUG_RE}`,
      );
      continue;
    }
    const abs = path.resolve(REPO_ROOT, entry.stlPath);
    try {
      const stat = await fs.stat(abs);
      out.push({
        ...entry,
        downloadUrl: `/api/accessories/${entry.slug}`,
        fileSize: stat.size,
      });
    } catch (e) {
      if ((e as NodeJS.ErrnoException).code === "ENOENT") {
        console.warn(
          `[accessories] catalog entry "${entry.slug}" references missing STL at ${entry.stlPath}`,
        );
        continue;
      }
      throw e;
    }
  }
  return out;
}

/** Look up a single accessory by slug, or null if not found / missing on disk. */
export async function getAccessoryBySlug(
  slug: string,
): Promise<AccessoryEntry | null> {
  if (!SAFE_SLUG_RE.test(slug)) return null;
  const all = await listAccessories();
  return all.find((a) => a.slug === slug) ?? null;
}

/**
 * Every accessory compatible with the given model stem. Stems are
 * `.scad` filenames without the extension (e.g. "cylindrical_holder_slot").
 * Returns `[]` for unknown stems — callers render no UI in that case.
 */
export async function getAccessoriesForModel(
  modelStem: string,
): Promise<AccessoryEntry[]> {
  const all = await listAccessories();
  return all.filter((a) => a.compatibleModels.includes(modelStem));
}

/**
 * Reverse lookup: every model stem an accessory pairs with. Pulled
 * straight from the catalog (no on-disk model verification — that
 * belongs to the model's own discovery layer). Returns `[]` if the
 * accessory slug is unknown.
 */
export async function getModelsForAccessory(slug: string): Promise<string[]> {
  const entry = ACCESSORIES.find((a) => a.slug === slug);
  return entry ? [...entry.compatibleModels] : [];
}
