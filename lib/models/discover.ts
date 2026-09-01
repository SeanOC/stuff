// Filesystem-backed model discovery. Used by the gallery (/) and the
// dynamic model page (/models/[slug]) — both server components, both
// allowed to hit the disk.
//
// Runtime scan rather than a build-time emitted manifest: keeps the
// pipeline simple, stays fresh on file changes during dev, and avoids
// a separate build step. With <50 models the cost is negligible.

import fs from "node:fs/promises";
import path from "node:path";
import { parseScadParams, type Param, type Preset } from "../scad-params/parse";
import { CATALOG, BUILD123D_CATALOG, type CategoryId } from "./catalog";
import { bdModelsEnabled, loadBdManifest } from "./bd-manifest";

const MODELS_DIR = path.resolve(process.cwd(), "models");

export interface ModelEntry {
  /**
   * Geometry engine. "scad" for the models/ .scad sources, "build123d"
   * for models discovered from build123d/manifest.json.
   */
  engine: "scad" | "build123d";
  /** Filename stem, e.g. "cylindrical_holder_slot". */
  stem: string;
  /** URL-safe slug derived from stem, dashes for underscores. */
  slug: string;
  /** Repo-relative path, e.g. "models/cylindrical_holder_slot.scad". */
  modelPath: string;
  /** First non-blank comment line, or stem-derived fallback. */
  title: string;
  /** Whether the file has any inline @param annotations. */
  annotated: boolean;
  /** Number of parsed @param annotations. */
  paramCount: number;
  /** Catalog category (SCAD) or the manifest's categoryId (build123d). */
  categoryId: string;
  /** Two-line library card blurb. Joined from lib/models/catalog.ts. */
  blurb: string;
}

export interface ModelDetail extends ModelEntry {
  source: string;
  params: Param[];
  /** Stock presets declared inline via `@preset` in the .scad source. */
  presets: Preset[];
  warnings: string[];
}

/** List every model in `models/`. Sorted alphabetically by stem. */
export async function listModels(): Promise<ModelEntry[]> {
  const entries = await fs.readdir(MODELS_DIR);
  const stems = entries
    .filter((f) => f.endsWith(".scad"))
    .map((f) => f.slice(0, -".scad".length))
    .sort();

  const scadModels = await Promise.all(stems.map(async (stem) => {
    const modelPath = `models/${stem}.scad`;
    const source = await fs.readFile(path.join(MODELS_DIR, `${stem}.scad`), "utf8");
    const { params } = parseScadParams(source);
    const catalogEntry = CATALOG[stem];
    if (!catalogEntry) {
      throw new Error(
        `No catalog entry for "${stem}". Add it to lib/models/catalog.ts.`,
      );
    }
    return {
      engine: "scad" as const,
      stem,
      slug: stemToSlug(stem),
      modelPath,
      title: deriveTitle(source, stem),
      annotated: params.length > 0,
      paramCount: params.length,
      categoryId: catalogEntry.categoryId,
      blurb: catalogEntry.blurb,
    };
  }));

  // build123d models come from the generated manifest (P1a, pst-dsiq).
  // Flag-gated (BD_MODELS_ENABLED, default off): their detail routes
  // don't exist until P1c, so the gallery must not link to them yet.
  // The machinery + merge tests land with the flag off.
  const bdModels = bdModelsEnabled()
    ? await listBdModels()
    : [];

  return [...scadModels, ...bdModels].sort(
    (a, b) => a.slug.localeCompare(b.slug),
  );
}

/**
 * build123d models from the generated manifest, merged into the same
 * ModelEntry shape. Titles/blurb/category come from the manifest, but
 * the category id must still be a real CATALOG category and each slug
 * must have a BUILD123D_CATALOG entry — same no-entry-throws enforcement
 * as SCAD models (the manifest's categoryId is cross-checked against
 * the catalog here so a drift fails loud rather than mis-shelving the
 * card).
 */
export async function listBdModels(): Promise<ModelEntry[]> {
  const manifest = await loadBdManifest();
  return manifest.models.map((m) => {
    const stem = slugToStem(m.slug);
    const catalogEntry = BUILD123D_CATALOG[stem];
    if (!catalogEntry) {
      throw new Error(
        `No catalog entry for build123d model "${stem}". ` +
          `Add it to BUILD123D_CATALOG in lib/models/catalog.ts.`,
      );
    }
    if (catalogEntry.categoryId !== (m.categoryId as CategoryId)) {
      throw new Error(
        `build123d manifest categoryId "${m.categoryId}" for "${stem}" ` +
          `does not match the catalog ("${catalogEntry.categoryId}"). ` +
          `Fix the registry or lib/models/catalog.ts, then regenerate ` +
          `build123d/manifest.json.`,
      );
    }
    return {
      engine: "build123d" as const,
      stem,
      slug: m.slug,
      modelPath: "build123d/manifest.json",
      title: m.title,
      annotated: m.params.length > 0,
      paramCount: m.params.length,
      categoryId: catalogEntry.categoryId,
      blurb: m.blurb,
    };
  });
}

/** Load one model by slug, or null if not found. */
export async function loadModel(slug: string): Promise<ModelDetail | null> {
  const stem = slugToStem(slug);
  if (!isSafeStem(stem)) return null;
  const abs = path.join(MODELS_DIR, `${stem}.scad`);
  let source: string;
  try {
    source = await fs.readFile(abs, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
  const { params, presets, warnings } = parseScadParams(source);
  const catalogEntry = CATALOG[stem];
  if (!catalogEntry) {
    throw new Error(
      `No catalog entry for "${stem}". Add it to lib/models/catalog.ts.`,
    );
  }
  return {
    engine: "scad",
    stem,
    slug,
    modelPath: `models/${stem}.scad`,
    title: deriveTitle(source, stem),
    annotated: params.length > 0,
    paramCount: params.length,
    categoryId: catalogEntry.categoryId,
    blurb: catalogEntry.blurb,
    source,
    params,
    presets,
    warnings,
  };
}

export function stemToSlug(stem: string): string {
  return stem.replaceAll("_", "-");
}

export function slugToStem(slug: string): string {
  return slug.replaceAll("-", "_");
}

function isSafeStem(stem: string): boolean {
  // After slug→stem conversion the only legal characters are
  // alphanumerics + underscore. Anything else (path separators,
  // dots, leading hyphen) means a hostile slug and we refuse it.
  return /^[A-Za-z0-9_]+$/.test(stem);
}

export function deriveTitle(source: string, stem: string): string {
  for (const raw of source.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (!line.startsWith("//")) break;
    const text = line.replace(/^\/\/+\s*/, "").trim();
    if (!text) continue;
    // Skip license-metadata lines so the SPDX/Copyright block that
    // leads every .scad file doesn't become the title. The title is
    // the first prose `//` line after any metadata header.
    if (/^SPDX-[A-Za-z]+-[A-Za-z]+:/i.test(text)) continue;
    if (/^Copyright\b/i.test(text)) continue;
    return text.replace(/[—–-]\s*$/, "").trim();
  }
  return stem.replaceAll("_", " ");
}
