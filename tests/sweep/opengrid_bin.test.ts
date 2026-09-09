import { sweepModel } from "./runner";

import { readFile } from "node:fs/promises";
import { describe, expect, it } from "vitest";
import { applyParamOverrides, parseScadParams } from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import { connectedComponentCount, isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";

sweepModel("opengrid_bin");

// The generic sweep changes one parameter from the openGrid default.
// Exercise the rounded intersection with Multiconnect selected as well.
const cases = [
  [1, 1], [1, 2], [6, 2], [2, 1], [2, 4], [1, 4], [6, 1], [6, 4],
];
describe("Multiconnect corner intersection extremes (pst-4fy0)", () => {
  for (const [width_units, height_units] of cases) {
    it(`${width_units}x${height_units}, maximum slot tolerance`, async () => {
      const source = await readFile("models/opengrid_bin.scad", "utf8");
      const { params } = parseScadParams(source);
      const result = await renderToStl({
        source: applyParamOverrides(source, params, {
          mount_type: "multiconnect", width_units, height_units,
          slot_tolerance: 1.075,
        }),
        fetchLibFile: async (name) => {
          try { return await readFile(`libs/${name}`, "utf8"); }
          catch { return null; }
        },
      });
      expect(result.ok, result.errorMessage).toBe(true);
      const triangles = parseStlTriangles(result.stl!);
      expect(triangles.length).toBeGreaterThan(0);
      expect(isWatertight(triangles)).toBe(true);
      expect(connectedComponentCount(triangles)).toBe(1);
    }, 300_000);
  }
});
