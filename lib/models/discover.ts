// Filesystem-backed model discovery. Used by the gallery (/) and the
// dynamic model page (/models/[slug]) — both server components, both
// allowed to hit the disk.
//
// Runtime scan rather than a build-time emitted manifest: keeps the
// pipeline simple, stays fresh on file changes during dev, and avoids
// a separate build step. With <50 models the cost is negligible.

import fs from "node:fs/promises";
import path from "node:path";
import { parseScadParams, type Param } from "../scad-params/parse";

const MODELS_DIR = path.resolve(process.cwd(), "models");

export interface ModelEntry {
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
}

export interface ModelDetail extends ModelEntry {
  source: string;
  params: Param[];
  warnings: string[];
}

/** List every model in `models/`. Sorted alphabetically by stem. */
export async function listModels(): Promise<ModelEntry[]> {
  const entries = await fs.readdir(MODELS_DIR);
  const stems = entries
    .filter((f) => f.endsWith(".scad"))
    .map((f) => f.slice(0, -".scad".length))
    .sort();

  return Promise.all(stems.map(async (stem) => {
    const modelPath = `models/${stem}.scad`;
    const source = await fs.readFile(path.join(MODELS_DIR, `${stem}.scad`), "utf8");
    const { params } = parseScadParams(source);
    return {
      stem,
      slug: stemToSlug(stem),
      modelPath,
      title: deriveTitle(source, stem),
      annotated: params.length > 0,
      paramCount: params.length,
    };
  }));
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
  const { params, warnings } = parseScadParams(source);
  return {
    stem,
    slug,
    modelPath: `models/${stem}.scad`,
    title: deriveTitle(source, stem),
    annotated: params.length > 0,
    paramCount: params.length,
    source,
    params,
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

function deriveTitle(source: string, stem: string): string {
  for (const raw of source.split(/\r?\n/)) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("//")) {
      const text = line.replace(/^\/\/+\s*/, "").trim();
      if (text) return text.replace(/[—–-]\s*$/, "").trim();
    }
    // Stop at the first non-comment, non-blank line — title only
    // comes from the file's leading comment block.
    break;
  }
  return stem.replaceAll("_", " ");
}
