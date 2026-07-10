// Demo + guard for the scripts/new-model.py scaffold (st-t71): runs it
// against a sandbox tree seeded with the REAL catalog.ts, then asserts
// the generated artifacts satisfy the same contracts the repo gates
// enforce (parseScadParams grammar, PRINT_ANCHOR_BBOX literal, sweep
// registration, catalog entry shape, clobber refusal). Render-level
// verification (watertight, snap pitch) is the invariants pipeline's
// job and needs openscad — out of scope here.

import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { parseScadParams } from "@/lib/scad-params/parse";

const ROOT = path.resolve(__dirname, "..");
const SCRIPT = path.join(ROOT, "scripts", "new-model.py");

let sandbox: string;

function runScaffold(...args: string[]) {
  return spawnSync("python3", [SCRIPT, ...args, "--root", sandbox], {
    encoding: "utf8",
  });
}

beforeAll(() => {
  sandbox = mkdtempSync(path.join(tmpdir(), "new-model-scaffold-"));
  mkdirSync(path.join(sandbox, "lib", "models"), { recursive: true });
  mkdirSync(path.join(sandbox, "models"), { recursive: true });
  mkdirSync(path.join(sandbox, "tests", "sweep"), { recursive: true });
  copyFileSync(
    path.join(ROOT, "lib", "models", "catalog.ts"),
    path.join(sandbox, "lib", "models", "catalog.ts"),
  );
});

afterAll(() => {
  rmSync(sandbox, { recursive: true, force: true });
});

describe("new-model.py scaffold", () => {
  it("generates all four artifacts for a plain model", () => {
    const res = runScaffold("zz_scaffold_demo", "--category", "storage");
    expect(res.status, res.stderr).toBe(0);

    const scad = readFileSync(
      path.join(sandbox, "models", "zz_scaffold_demo.scad"),
      "utf8",
    );
    // SPDX + copyright header, top of file.
    expect(scad.startsWith("// SPDX-License-Identifier:")).toBe(true);
    // Literal PRINT_ANCHOR_BBOX triple (expressions are invisible to
    // the invariants driver's regex).
    expect(scad).toMatch(/^PRINT_ANCHOR_BBOX = \[[\d.]+, [\d.]+, [\d.]+\];/m);

    // The generated param block must satisfy the REAL parser the
    // webapp and sweep runner use.
    const parsed = parseScadParams(scad);
    expect(parsed.params.length).toBeGreaterThan(0);
    expect(parsed.presets.length).toBeGreaterThan(0);
    expect(parsed.warnings).toEqual([]);

    // Invariants sidecar stub with the standard topology pin.
    const sidecar = readFileSync(
      path.join(sandbox, "models", "zz_scaffold_demo.invariants.py"),
      "utf8",
    );
    expect(sidecar).toContain("def check(ctx):");
    expect(sidecar).toContain("expect_connected_solids(ctx, 1)");

    // Sweep registration exactly matches the per-model file shape
    // coverage.test.ts requires.
    const sweep = readFileSync(
      path.join(sandbox, "tests", "sweep", "zz_scaffold_demo.test.ts"),
      "utf8",
    );
    expect(sweep).toContain('sweepModel("zz_scaffold_demo")');

    // Catalog entry appended, block still well-formed.
    const catalog = readFileSync(
      path.join(sandbox, "lib", "models", "catalog.ts"),
      "utf8",
    );
    expect(catalog).toMatch(/^ {2}zz_scaffold_demo: \{$/m);
    expect(catalog).toContain('categoryId: "storage"');
    expect(catalog).toMatch(/\},\n\};/);
  });

  it("refuses to clobber on re-run and leaves the tree untouched", () => {
    const before = readFileSync(
      path.join(sandbox, "lib", "models", "catalog.ts"),
      "utf8",
    );
    const res = runScaffold("zz_scaffold_demo", "--category", "storage");
    expect(res.status).not.toBe(0);
    expect(res.stderr).toContain("refusing to clobber");
    const after = readFileSync(
      path.join(sandbox, "lib", "models", "catalog.ts"),
      "utf8",
    );
    expect(after).toBe(before);
  });

  it("emits the openGrid conventions with --opengrid", () => {
    const res = runScaffold("zz_og_demo", "--category", "multiboard", "--opengrid");
    expect(res.status, res.stderr).toBe(0);

    const scad = readFileSync(
      path.join(sandbox, "models", "zz_og_demo.scad"),
      "utf8",
    );
    // The vendored snap module, `use`d not `include`d (trailing demo call).
    expect(scad).toContain("use <QuackWorks/openGrid/opengrid-snap.scad>");
    expect(scad).not.toContain("include <QuackWorks");
    // 28mm pitch + welded directional wrapper, strong nub up.
    expect(scad).toContain("snap_pitch = 28;");
    expect(scad).toContain("module welded_directional_snap()");
    expect(scad).toContain("directional = true");
    expect(parseScadParams(scad).warnings).toEqual([]);

    const sidecar = readFileSync(
      path.join(sandbox, "models", "zz_og_demo.invariants.py"),
      "utf8",
    );
    expect(sidecar).toContain("_SNAP_PITCH = 28.0");
    expect(sidecar).toContain("expect_connected_solids(ctx, 1)");
  });

  it("rejects a category not present in MODEL_CATEGORIES", () => {
    const res = runScaffold("zz_bad_cat", "--category", "widgets");
    expect(res.status).not.toBe(0);
    expect(res.stderr).toContain("unknown category");
    // Error names the valid ids so the caller doesn't grep for them.
    expect(res.stderr).toContain("multiboard");
  });

  it("rejects a non-snake_case stem", () => {
    const res = runScaffold("Bad-Stem", "--category", "storage");
    expect(res.status).not.toBe(0);
    expect(res.stderr).toContain("snake_case");
  });
});
