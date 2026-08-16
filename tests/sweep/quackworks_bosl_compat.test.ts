// Vendored-lib compatibility probe (pst-990o).
//
// The BOSL2 pin is fbcdfdd5 (v2.0.747), which asserts is_finite(spin) and
// cylinder h>0, so the QuackWorks BOSL2 connector generators used to break
// two ways: vector spin=[x,y,z] calls, and the zero-height oct_prism helper
// at the documented flush-fit setting (offset / Snap_Connector_Height = 0).
// Patch 0004 migrates the spins and guards every oct_prism copy. This probe
// renders the affected generators through the same wasm path the site
// preview uses, against the vendored BOSL2, so a future BOSL2 bump (or a
// dropped patch) that reintroduces either break is caught here, not only by
// the external codex gate.
//
// Coverage note: multiconnectGenerator exercises the rail() vector-spin
// migration; snapConnectBacker(offset=0) exercises BOTH the offset_sweep
// vector-spin migration AND the zero-height oct_prism guard in one render.
// The Underware_Connectors / Underware_keyholes generators also carry the
// guarded oct_prism, but they include BOSL2/threading.scad + Minkowski and
// do NOT render on the wasm engine at all (pre-existing, pin-independent —
// they abort on wasm even at defaults), so they cannot be probed here; the
// codex gate renders them on desktop CGAL, where they were verified to match
// the 456fcd8 baseline at Snap_Connector_Height=0. No catalog model uses any
// of these BOSL2 modules, so nothing else in the sweep exercises them.

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

async function expectRenders(source: string) {
  const res = await renderToStl({ source, fetchLibFile: fetchLibFromDisk });
  const hardError = hardErrorFrom(res.stderr);
  expect(hardError, `hard error: ${hardError}`).toBeNull();
  expect(res.ok, `render failed: ${res.errorMessage}`).toBe(true);
  const tris = parseStlTriangles(res.stl!);
  expect(tris.length, "no triangles").toBeGreaterThan(0);
  expect(isWatertight(tris), "not watertight").toBe(true);
}

describe("QuackWorks BOSL2 vector-spin + h=0 compat (vendored pin)", () => {
  // include (not use) so the module's own `include <BOSL2/std.scad>` runs in
  // scope, establishing BOSL2 tag/anchor special-var defaults.
  const genParts: Record<string, string> = {
    "connector-round":
      'GeneratePart(Length=0, Select_Profile="Standard", Select_Part_Type="Connector Round", Dimples="Enabled", OnRamps="Disabled");',
    "connector-double-sided-round":
      'GeneratePart(Length=0, Select_Profile="Standard", Select_Part_Type="Connector Double sided Round", Dimples="Enabled", OnRamps="Disabled");',
  };
  for (const [label, call] of Object.entries(genParts)) {
    it(
      `multiconnectGenerator renders ${label} under the vendored BOSL2`,
      () =>
        expectRenders(
          "include <QuackWorks/Modules/multiconnectGenerator.scad>\n" + call,
        ),
      PER_RENDER_TIMEOUT_MS,
    );
  }

  it(
    "snapConnectBacker renders flush (offset=0: oct_prism h=0 guard + offset_sweep spin)",
    () =>
      expectRenders(
        "include <BOSL2/std.scad>\n" +
          "use <QuackWorks/Modules/snapConnector.scad>\n" +
          "snapConnectBacker(offset=0, holdingTolerance=1);",
      ),
    PER_RENDER_TIMEOUT_MS,
  );
});
