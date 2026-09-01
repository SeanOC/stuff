// Server-side twin of .githooks/pre-commit: keeps models/ and the
// static CATALOG in lockstep even when the hook is bypassed
// (--no-verify, or a clone that never ran scripts/setup-git-hooks.sh).
//
// listModels() already throws on a .scad with no catalog entry, but
// that failure surfaces as a generic error inside unrelated tests.
// These assertions name the exact file/key and the fix. The reverse
// direction (dangling catalog key) and the invariants-sidecar
// convention are covered nowhere else.

import fs from "node:fs";
import path from "node:path";
import { readFileSync } from "node:fs";
import { describe, expect, it, beforeAll } from "vitest";
import { CATALOG, BUILD123D_CATALOG } from "./catalog";

const MODELS_DIR = path.resolve(process.cwd(), "models");

const stems = fs
  .readdirSync(MODELS_DIR)
  .filter((f) => f.endsWith(".scad"))
  .map((f) => f.slice(0, -".scad".length));

// The committed build123d manifest (emitter contract — see
// build123d/scripts/manifest.py). Parsed once for the BD parity tests.
let bdManifestSlugs: string[] = [];
beforeAll(() => {
  try {
    const doc = JSON.parse(
      readFileSync(path.resolve(process.cwd(), "build123d", "manifest.json"), "utf8"),
    );
    bdManifestSlugs = (doc.models as Array<{ slug: string }>).map((m) => m.slug);
  } catch {
    bdManifestSlugs = [];
  }
});

describe("models/ <-> CATALOG parity", () => {
  it("every models/<stem>.scad has a CATALOG entry", () => {
    const missing = stems.filter((stem) => !(stem in CATALOG));
    expect(
      missing,
      `No catalog entry for: ${missing.join(", ")}. ` +
        `Add a "<stem>: { categoryId, blurb }" block to lib/models/catalog.ts — ` +
        `without it listModels() throws and the model never appears in prod.`,
    ).toEqual([]);
  });

  it("every CATALOG key has a models/<key>.scad (no dangling entries)", () => {
    const dangling = Object.keys(CATALOG).filter(
      (key) => !stems.includes(key),
    );
    expect(
      dangling,
      `Dangling CATALOG keys: ${dangling.join(", ")}. ` +
        `Delete the entry from lib/models/catalog.ts or restore the matching .scad.`,
    ).toEqual([]);
  });

  it("every models/<stem>.scad has an invariants sidecar", () => {
    const missing = stems.filter(
      (stem) => !fs.existsSync(path.join(MODELS_DIR, `${stem}.invariants.py`)),
    );
    expect(
      missing,
      `Missing models/<stem>.invariants.py for: ${missing.join(", ")}. ` +
        `Every model ships one (skeleton in AGENTS.md, "Per-model invariants").`,
    ).toEqual([]);
  });
});

describe("build123d/ <-> BUILD123D_CATALOG parity", () => {
  it("every manifest model has a BUILD123D_CATALOG entry", () => {
    const missing = bdManifestSlugs.filter(
      (slug) => !(slug.replace(/-/g, "_") in BUILD123D_CATALOG),
    );
    expect(
      missing,
      `No BUILD123D_CATALOG entry for: ${missing.join(", ")}. ` +
        `Add a "<stem>: { categoryId, blurb }" block to lib/models/catalog.ts — ` +
        `without it listBdModels() throws and the model never appears in the gallery.`,
    ).toEqual([]);
  });

  it("every BUILD123D_CATALOG key has a manifest model (no dangling entries)", () => {
    const bdStems = bdManifestSlugs.map((slug) => slug.replace(/-/g, "_"));
    const dangling = Object.keys(BUILD123D_CATALOG).filter(
      (stem) => !bdStems.includes(stem),
    );
    expect(
      dangling,
      `Dangling BUILD123D_CATALOG keys: ${dangling.join(", ")}. ` +
        `Delete the entry from lib/models/catalog.ts or regenerate ` +
        `build123d/manifest.json (uv run python scripts/manifest.py).`,
    ).toEqual([]);
  });

  it("manifest categoryId matches BUILD123D_CATALOG for every model", () => {
    const doc = JSON.parse(
      readFileSync(path.resolve(process.cwd(), "build123d", "manifest.json"), "utf8"),
    );
    const mismatches = (doc.models as Array<{ slug: string; categoryId: string }>)
      .map((m) => ({
        stem: m.slug.replace(/-/g, "_"),
        catalog: BUILD123D_CATALOG[m.slug.replace(/-/g, "_")]?.categoryId,
        manifest: m.categoryId,
      }))
      .filter((x) => x.catalog !== undefined && x.catalog !== x.manifest);
    expect(
      mismatches,
      `Manifest/catalog categoryId drift: ${JSON.stringify(mismatches)}. ` +
        `Fix the registry or lib/models/catalog.ts, then regenerate the manifest.`,
    ).toEqual([]);
  });
});
