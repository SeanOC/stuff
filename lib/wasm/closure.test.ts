import { describe, expect, it } from "vitest";
import { buildIncludeClosure, extractImports, extractIncludes } from "./closure";

describe("extractIncludes", () => {
  it("pulls include and use directives", () => {
    const src = `
      include <BOSL2/std.scad>
      use <QuackWorks/Modules/snapConnector.scad>
        // commented include should NOT match — but our naive regex does
      include <other.scad>
    `;
    expect(extractIncludes(src)).toEqual([
      "BOSL2/std.scad",
      "QuackWorks/Modules/snapConnector.scad",
      "other.scad",
    ]);
  });

  it("handles whitespace inside angle brackets", () => {
    expect(extractIncludes("include < spaced/path.scad >")).toEqual([
      "spaced/path.scad",
    ]);
  });
});

describe("buildIncludeClosure", () => {
  it("walks a chain of includes and returns each file once", async () => {
    const lib: Record<string, string> = {
      "a.scad": "include <b.scad>",
      "b.scad": "include <c.scad>",
      "c.scad": "// leaf",
    };
    const result = await buildIncludeClosure({
      entrySource: "include <a.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    expect(result.files.map((f) => f.fsPath)).toEqual([
      "/libraries/a.scad",
      "/libraries/b.scad",
      "/libraries/c.scad",
    ]);
    expect(result.missing).toEqual([]);
  });

  it("survives cycles", async () => {
    const lib: Record<string, string> = {
      "a.scad": "include <b.scad>",
      "b.scad": "include <a.scad>",
    };
    const result = await buildIncludeClosure({
      entrySource: "include <a.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    expect(result.files.map((f) => f.fsPath).sort()).toEqual([
      "/libraries/a.scad",
      "/libraries/b.scad",
    ]);
  });

  it("reports missing files but keeps walking the rest", async () => {
    const lib: Record<string, string> = {
      "a.scad": "include <missing.scad>\ninclude <c.scad>",
      "c.scad": "// leaf",
    };
    const result = await buildIncludeClosure({
      entrySource: "include <a.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    expect(result.missing).toContain("missing.scad");
    expect(result.files.map((f) => f.fsPath)).toContain("/libraries/c.scad");
  });

  it("respects maxFiles and stops walking past the cap", async () => {
    const lib: Record<string, string> = {};
    for (let i = 0; i < 10; i++) {
      lib[`f${i}.scad`] = `include <f${i + 1}.scad>`;
    }
    lib["f10.scad"] = "// leaf";
    const result = await buildIncludeClosure({
      entrySource: "include <f0.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
      maxFiles: 3,
    });
    expect(result.files).toHaveLength(3);
  });

  it("resolves sibling-relative includes from the parent's dir", async () => {
    const lib: Record<string, string> = {
      "BOSL2/std.scad": "include <util.scad>",
      "BOSL2/util.scad": "// leaf",
    };
    const result = await buildIncludeClosure({
      entrySource: "include <BOSL2/std.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    const paths = result.files.map((f) => f.fsPath).sort();
    expect(paths).toContain("/libraries/BOSL2/std.scad");
    expect(paths).toContain("/libraries/BOSL2/util.scad");
    // The as-is probe (`util.scad`) is expected to 404; that's a
    // normal resolution step, not a genuinely missing file.
    expect(result.missing).toEqual([]);
  });

  it("only reports missing when every candidate fails", async () => {
    const lib: Record<string, string> = {
      "BOSL2/std.scad": "include <util.scad>\ninclude <truly_gone.scad>",
      "BOSL2/util.scad": "// leaf",
    };
    const result = await buildIncludeClosure({
      entrySource: "include <BOSL2/std.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    expect(result.missing).toEqual(["truly_gone.scad"]);
  });

  it("does not flag already-resolved includes as missing", async () => {
    // Entry pulls in BOSL2/std.scad at lib-root, then a sub-lib
    // `include <BOSL2/std.scad>` from inside QuackWorks/Modules/. The
    // resolver should recognize the lib-root path is already loaded
    // and skip the sibling probe entirely.
    const lib: Record<string, string> = {
      "BOSL2/std.scad": "// leaf",
      "QuackWorks/Modules/slot.scad": "include <BOSL2/std.scad>",
    };
    const result = await buildIncludeClosure({
      entrySource:
        "include <BOSL2/std.scad>\nuse <QuackWorks/Modules/slot.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
    });
    expect(result.missing).toEqual([]);
    expect(result.files.map((f) => f.fsPath).sort()).toEqual([
      "/libraries/BOSL2/std.scad",
      "/libraries/QuackWorks/Modules/slot.scad",
    ]);
  });
});

describe("extractImports", () => {
  it("pulls literal-string import targets, deduped", () => {
    const src = `
      import("mesh_a.stl", convexity = 10);
      translate([0, 0, 5]) import("mesh_a.stl");
      import(file = "mesh_b.stl");
    `;
    expect(extractImports(src)).toEqual(["mesh_a.stl", "mesh_b.stl"]);
  });

  it("skips commented-out imports", () => {
    const src = `
      // import("ghost.stl") — mentioned in a comment only
      import("real.stl");
    `;
    expect(extractImports(src)).toEqual(["real.stl"]);
  });

  it("returns nothing for import-free sources", () => {
    expect(extractImports("include <BOSL2/std.scad>\ncube(1);")).toEqual([]);
  });
});

describe("buildIncludeClosure import() assets", () => {
  it("fetches entry-level import targets and mounts them at the FS root", async () => {
    const bytes = new Uint8Array([0x53, 0x54, 0x4c, 0x00]);
    const result = await buildIncludeClosure({
      entrySource: 'import("mesh.stl", convexity = 10);',
      fetchLibFile: async () => null,
      fetchAssetFile: async (p) => (p === "mesh.stl" ? bytes : null),
    });
    expect(result.missing).toEqual([]);
    expect(result.assets).toEqual([{ fsPath: "/mesh.stl", data: bytes }]);
  });

  it("reports unresolvable import targets as missing", async () => {
    const result = await buildIncludeClosure({
      entrySource: 'import("gone.stl");',
      fetchLibFile: async () => null,
      fetchAssetFile: async () => null,
    });
    expect(result.assets).toEqual([]);
    expect(result.missing).toEqual(["gone.stl"]);
  });

  it("reports import targets as missing when no asset fetcher is supplied", async () => {
    const result = await buildIncludeClosure({
      entrySource: 'import("mesh.stl");',
      fetchLibFile: async () => null,
    });
    expect(result.assets).toEqual([]);
    expect(result.missing).toEqual(["mesh.stl"]);
  });

  it("does not scan lib files for imports", async () => {
    const lib: Record<string, string> = {
      "demo.scad": 'import("lib_side_demo.stl");',
    };
    const fetched: string[] = [];
    const result = await buildIncludeClosure({
      entrySource: "use <demo.scad>",
      fetchLibFile: async (p) => lib[p] ?? null,
      fetchAssetFile: async (p) => {
        fetched.push(p);
        return null;
      },
    });
    expect(fetched).toEqual([]);
    expect(result.assets).toEqual([]);
    expect(result.missing).toEqual([]);
  });
});
