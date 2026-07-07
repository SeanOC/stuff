import { execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  hardErrorFrom,
  isRetryableError,
  renderToStl,
  unresolvedFrom,
} from "./render";

// The pure guards decide "is this render actually good?" — the whole
// point of the wrapper (mirrors lib/wasm/render.ts). A regression here
// is how a partial/empty STL sneaks out as a success (st-7x7, st-zph).
describe("hardErrorFrom", () => {
  it("finds the first hard ERROR line", () => {
    expect(hardErrorFrom(["WARNING: x", "ERROR: boom", "ERROR: second"]))
      .toBe("ERROR: boom");
  });
  it("matches leading-whitespace and mixed case", () => {
    expect(hardErrorFrom(["  error: indented"])).toBe("  error: indented");
  });
  it("returns null when clean (a plain WARNING is not a hard error)", () => {
    expect(hardErrorFrom(["WARNING: mild", "Geometries in cache: 3"])).toBeNull();
  });
});

describe("unresolvedFrom", () => {
  it("captures unopenable include/library/import targets", () => {
    const lines = [
      "WARNING: Can't open include file 'BOSL2/std.scad'.",
      "WARNING: Can't open library 'foo.scad'.",
      "WARNING: Can't open import file 'mesh.stl'.",
    ];
    expect(unresolvedFrom(lines)).toEqual(["BOSL2/std.scad", "foo.scad", "mesh.stl"]);
  });
  it("ignores unrelated warnings", () => {
    expect(unresolvedFrom(["WARNING: something else"])).toEqual([]);
  });
});

describe("isRetryableError", () => {
  it("retries CGAL-class errors only", () => {
    expect(isRetryableError("ERROR: CGAL error in convex_hull_3")).toBe(true);
    expect(isRetryableError("ERROR: Parser error: syntax error")).toBe(false);
  });
});

// Integration: drives real openscad end-to-end. Skips where openscad
// isn't on PATH (e.g. the node-only CI job) so the suite still passes.
const HAVE_OPENSCAD = (() => {
  try {
    execFileSync("openscad", ["--version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
})();

describe.skipIf(!HAVE_OPENSCAD)("renderToStl (live openscad)", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "render-test-"));

  it("renders a trivial model to a non-empty STL", async () => {
    const model = path.join(dir, "ok.scad");
    writeFileSync(model, "cube([10,10,10]);\n");
    const r = await renderToStl({ modelPath: model, defines: [], openscadPath: dir, xvfb: false });
    expect(r.ok).toBe(true);
    expect(r.stl && r.stl.length).toBeGreaterThan(0);
    expect(r.errorMessage).toBeUndefined();
  });

  it("fails (no STL) on a hard openscad ERROR — never a bogus success", async () => {
    const model = path.join(dir, "bad.scad");
    writeFileSync(model, 'assert(false, "boom");\ncube(1);\n');
    const r = await renderToStl({ modelPath: model, defines: [], openscadPath: dir, xvfb: false });
    expect(r.ok).toBe(false);
    expect(r.stl).toBeUndefined();
    expect(r.errorMessage).toMatch(/assert|ERROR/i);
  });
});
