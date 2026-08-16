// Vendored-lib compatibility probe (pst-990o).
//
// The BOSL2 pin is fbcdfdd5 (v2.0.747), which asserts is_finite(spin)
// and so rejects the vector spin=[x,y,z] calls that the QuackWorks
// BOSL2 connector generators used. Patch 0004 migrates those calls; this
// probe renders the README-advertised multiconnectGenerator through the
// same wasm path the site preview uses, against the vendored BOSL2, so a
// future BOSL2 bump (or a dropped patch) that reintroduces the break is
// caught here instead of only by the external codex gate.
//
// No catalog model uses these BOSL2 modules, so nothing else in the
// sweep exercises them.

import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { renderToStl, hardErrorFrom } from "@/lib/wasm/render";
import { isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";

const ROOT = path.resolve(__dirname, "../..");
const PER_RENDER_TIMEOUT_MS = 300_000;

async function fetchLibFromDisk(relPath: string): Promise<string | null> {
  try {
    return await readFile(path.join(ROOT, "libs", relPath), "utf8");
  } catch {
    return null;
  }
}

// Each probe includes the generator (bringing its file-scope globals into
// scope) and then draws one advertised part with explicit named args.
const PARTS: Record<string, string> = {
  "connector-round":
    'GeneratePart(Length=0, Select_Profile="Standard", Select_Part_Type="Connector Round", Dimples="Enabled", OnRamps="Disabled");',
  "connector-double-sided-round":
    'GeneratePart(Length=0, Select_Profile="Standard", Select_Part_Type="Connector Double sided Round", Dimples="Enabled", OnRamps="Disabled");',
};

describe("QuackWorks BOSL2 vector-spin compat (vendored pin)", () => {
  for (const [label, call] of Object.entries(PARTS)) {
    it(
      `multiconnectGenerator renders ${label} under the vendored BOSL2`,
      async () => {
        // include (not use) so the generator's own `include <BOSL2/std.scad>`
        // runs in scope, establishing BOSL2 tag/anchor special-var defaults.
        // The file's default top-level render also runs (Select_Part_Type
        // default); the appended call draws the part under test.
        const source =
          "include <QuackWorks/Modules/multiconnectGenerator.scad>\n" +
          call;
        const res = await renderToStl({ source, fetchLibFile: fetchLibFromDisk });
        const hardError = hardErrorFrom(res.stderr);
        expect(hardError, `hard error: ${hardError}`).toBeNull();
        expect(res.ok, `render failed: ${res.errorMessage}`).toBe(true);
        expect(res.stl && res.stl.byteLength, "empty STL").toBeGreaterThan(0);
        const tris = parseStlTriangles(res.stl!);
        expect(tris.length, "no triangles").toBeGreaterThan(0);
        expect(isWatertight(tris), "not watertight").toBe(true);
      },
      PER_RENDER_TIMEOUT_MS,
    );
  }
});
