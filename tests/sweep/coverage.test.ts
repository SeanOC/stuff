// Meta-guard: every catalog model must have a per-model sweep file.
// Per-model files (rather than one loop) let vitest parallelize the
// sweep across workers; this test keeps that layout from silently
// dropping coverage when a new model lands.

import { readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = path.resolve(__dirname, "../..");

describe("sweep coverage", () => {
  it("has a sweep test file for every models/*.scad", () => {
    const stems = readdirSync(path.join(ROOT, "models"))
      .filter((f) => f.endsWith(".scad"))
      .map((f) => f.replace(/\.scad$/, ""));
    const sweepFiles = new Set(readdirSync(__dirname));
    const missing = stems.filter((s) => !sweepFiles.has(`${s}.test.ts`));
    expect(
      missing,
      `models without a sweep file — add tests/sweep/<stem>.test.ts: ${missing.join(", ")}`,
    ).toEqual([]);
  });
});
