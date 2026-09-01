// build123d manifest ingestion — the app-facing side of
// build123d/manifest.json (emitted by build123d/scripts/manifest.py,
// freshness-gated in .github/workflows/bd123.yml).
//
// The emitter's docstring pins the serialization contract to
// lib/scad-params/parse.ts: param objects are exactly the app's
// `Param` shapes (only-set keys, canonical order) and presets are
// `{id, label, values}`. So a well-formed manifest deserializes
// verbatim into `Param[]`/`Preset[]`.

import fs from "node:fs/promises";
import path from "node:path";
import type { Param, Preset } from "../scad-params/parse";
import type { CategoryId } from "./catalog";
import { slugToStem } from "./discover";

const MANIFEST_PATH = path.resolve(process.cwd(), "build123d", "manifest.json");

export type BdParam = Param & {
  /** Manifest extension: display unit hint. Tolerated but not relied on. */
  unit?: string;
};

export interface BdModel {
  /** URL-safe slug straight from the manifest (dashes, no conversion). */
  slug: string;
  title: string;
  blurb: string;
  categoryId: CategoryId;
  params: BdParam[];
  presets: Preset[];
}

export interface BdManifest {
  schemaVersion: number;
  models: BdModel[];
}

/** True when every field on every entry satisfies the emitter contract. */
function isBdModel(value: unknown): value is BdModel {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.slug === "string" &&
    /^[A-Za-z0-9-]+$/.test(v.slug) &&
    typeof v.engine === "string" &&
    v.engine === "build123d" &&
    typeof v.title === "string" &&
    v.title.length > 0 &&
    typeof v.blurb === "string" &&
    v.blurb.length > 0 &&
    typeof v.categoryId === "string" &&
    Array.isArray(v.params) &&
    Array.isArray(v.presets)
  );
}

/**
 * Read + shape-check the committed manifest. A missing file yields an
 * empty model list (discovery degrades to SCAD-only) so a checkout
 * without the build123d tree never breaks the gallery; a file that
 * EXISTS but is malformed throws — a silent catalog entry that would
 * be dropped server-side is worse than a loud startup failure.
 */
export async function loadBdManifest(): Promise<BdManifest> {
  let raw: string;
  try {
    raw = await fs.readFile(MANIFEST_PATH, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return { schemaVersion: 1, models: [] };
    }
    throw e;
  }
  const doc: unknown = JSON.parse(raw);
  if (
    typeof doc !== "object" ||
    doc === null ||
    typeof (doc as BdManifest).schemaVersion !== "number" ||
    (doc as BdManifest).schemaVersion !== 1 ||
    !Array.isArray((doc as BdManifest).models)
  ) {
    throw new Error(
      "build123d/manifest.json: expected { schemaVersion: 1, models: [...] }",
    );
  }
  for (const model of (doc as BdManifest).models) {
    if (!isBdModel(model)) {
      throw new Error(
        `build123d/manifest.json: malformed entry ${JSON.stringify(
          model,
        ).slice(0, 120)}… (run build123d/scripts/manifest.py to regenerate)`,
      );
    }
  }
  return doc as BdManifest;
}

/**
 * Load one build123d model by its manifest slug, or null if the slug
 * is unknown. Read side for the detail page (P1c) and the preset-asset
 * serving route: both need the manifest's preset allowlist keyed by
 * slug. Shares loadBdManifest's shape-check, so a malformed manifest
 * throws here too.
 */
export async function loadBdModel(slug: string): Promise<BdModel | null> {
  const manifest = await loadBdManifest();
  return manifest.models.find((m) => m.slug === slug) ?? null;
}

/**
 * Feature flag: build123d models only appear in the gallery once the
 * detail-view side of the epic (P1c) exists. Default OFF. Set
 * BD_MODELS_ENABLED=1 in the Vercel project env to activate — the same
 * switch also turns on the build-time preset bake (scripts/bake-bd-
 * presets.sh, chained into the `prebuild` npm hook), so one env var
 * gates both the feature and the assets it needs. Leaving it unset
 * keeps CI and every other build untouched.
 */
export function bdModelsEnabled(): boolean {
  return process.env.BD_MODELS_ENABLED === "1";
}
