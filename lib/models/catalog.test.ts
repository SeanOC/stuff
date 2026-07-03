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
import { describe, expect, it } from "vitest";
import { CATALOG } from "./catalog";

const MODELS_DIR = path.resolve(process.cwd(), "models");

const stems = fs
  .readdirSync(MODELS_DIR)
  .filter((f) => f.endsWith(".scad"))
  .map((f) => f.slice(0, -".scad".length));

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
