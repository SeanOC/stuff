import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  applyParamOverrides,
  defaultsOf,
  parseScadParams,
} from "@/lib/scad-params/parse";
import { hardErrorFrom, isRetryableError, renderToStl } from "./render";
import {
  connectedComponentCount,
  isWatertight,
  parseStlTriangles,
} from "./stl-analysis";

// Transcript recorded from the st-7x7 failure: OpenSCAD hit a CGAL
// assertion inside hull(), logged ERROR, dropped the hull's geometry —
// and still exited 0 with a non-empty (shattered) STL.
const CGAL_EXIT0_TRANSCRIPT = [
  "Could not initialize localization (application path is '/').",
  "CGAL error: assertion violation!",
  "Expression : it != border.end()",
  "File       : /emsdk/upstream/emscripten/cache/sysroot/include/CGAL/convex_hull_3.h",
  "ERROR: CGAL error in applyHull(): CGAL ERROR: assertion violation!",
  "Total rendering time: 0:00:01.376",
  "   Facets:        568",
];

describe("hardErrorFrom", () => {
  it("finds the ERROR line in a CGAL exit-0 transcript", () => {
    expect(hardErrorFrom(CGAL_EXIT0_TRANSCRIPT)).toBe(
      "ERROR: CGAL error in applyHull(): CGAL ERROR: assertion violation!",
    );
  });

  it("ignores warnings and render summaries", () => {
    expect(
      hardErrorFrom([
        "WARNING: variable x not specified",
        "Total rendering time: 0:00:00.100",
        "   Facets:      18380",
      ]),
    ).toBeNull();
  });

  it("does not treat mid-line mentions of 'error' as hard errors", () => {
    expect(hardErrorFrom(["CGAL error: assertion violation!"])).toBeNull();
  });
});

describe("isRetryableError", () => {
  it("retries CGAL-class failures (randomized algorithms)", () => {
    expect(
      isRetryableError("ERROR: CGAL error in applyHull(): CGAL ERROR: assertion violation!"),
    ).toBe(true);
  });

  it("does not retry deterministic errors", () => {
    expect(isRetryableError('ERROR: Parser error: syntax error in file "", line 3')).toBe(false);
  });
});

describe("renderToStl (wasm integration)", () => {
  // st-zph: OpenSCAD only WARNs on an unreadable import() and renders
  // the rest of the tree — the export route shipped a blower mount
  // whose imported body was silently absent. A missing import() asset
  // must fail the render, not annotate it.
  it("fails when an import() asset cannot be fetched", async () => {
    const res = await renderToStl({
      source: 'import("gone.stl");\ncube(1);\n',
      fetchLibFile: async () => null,
      fetchAssetFile: async () => null,
    });
    expect(res.ok).toBe(false);
    expect(res.errorMessage).toMatch(/import\(\) asset not found: gone\.stl/);
    expect(res.missing).toContain("gone.stl");
  });

  it("fails when a model import()s but no asset fetcher is supplied", async () => {
    const res = await renderToStl({
      source: 'import("gone.stl");\n',
      fetchLibFile: async () => null,
    });
    expect(res.ok).toBe(false);
    expect(res.errorMessage).toMatch(/no fetchAssetFile supplied/);
  });

  it("fails rather than succeeding with partial geometry on a hard error", async () => {
    // Syntax error -> ERROR with nonzero exit; pins the error path
    // end-to-end without depending on a nondeterministic CGAL trip.
    const res = await renderToStl({
      source: "cube(1;\n",
      fetchLibFile: async () => null,
    });
    expect(res.ok).toBe(false);
    expect(res.errorMessage).toMatch(/ERROR|exit/i);
  }, 120_000);

  // st-7x7 operator repro: hex stylus at hex_width=9 through the exact
  // site pipeline (param override -> wasm render) must produce a single
  // watertight solid. Before the fix, CGAL's randomized hull could drop
  // the body and leave only the fin + ribs.
  it("renders the hex stylus at hex_width=9 as one watertight solid", async () => {
    const root = path.resolve(__dirname, "../..");
    const source = await readFile(
      path.join(root, "models/lcd_stylus_hex_8mm.scad"),
      "utf8",
    );
    const { params } = parseScadParams(source);
    const values = defaultsOf(params);
    values.hex_width = 9;
    const res = await renderToStl({
      source: applyParamOverrides(source, params, values),
      fetchLibFile: async () => null,
    });
    expect(res.ok).toBe(true);
    expect(res.errorMessage).toBeUndefined();
    const tris = parseStlTriangles(res.stl!);
    expect(tris.length).toBeGreaterThan(1000);
    expect(connectedComponentCount(tris)).toBe(1);
    expect(isWatertight(tris)).toBe(true);
  }, 120_000);
});
