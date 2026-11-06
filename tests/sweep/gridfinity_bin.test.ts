import { sweepModel } from "./runner";
import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { applyParamOverrides, parseScadParams } from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import { connectedComponentCount, isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";

sweepModel("gridfinity_bin");

const ROOT = path.resolve(__dirname, "../..");
const source = readFileSync(path.join(ROOT, "models/gridfinity_bin.scad"), "utf8");
const { params, presets, warnings } = parseScadParams(source);

describe("Gridfinity total height including the stacking lip", () => {
  it("publishes the height controls and drawer test-fit preset", () => {
    expect(warnings).toEqual([]);
    expect(params.find((p) => p.name === "height_mode")).toMatchObject({
      default: "units", choices: ["units", "total mm"],
    });
    expect(params.find((p) => p.name === "height_units")).toMatchObject({
      default: 3, min: 2, max: 8,
    });
    expect(params.find((p) => p.name === "height_mm")).toMatchObject({
      min: 11, max: 120, step: 0.5,
    });
    expect(presets.find((p) => p.id === "test-fit-65mm")?.values).toMatchObject({
      grid_x: 1, grid_y: 1, height_mode: "total mm", height_mm: 65,
    });
  });

  // Both range ends, the four requested drawer tests, and a half-mm step.
  // The generic sweep varies one parameter at a time, so its height_mm
  // rows alone cannot exercise this mode-dependent dimension.
  for (const height_mm of [11, 60, 65, 65.5, 68, 70, 120]) {
    it(`1×1 at ${height_mm}mm total`, async () => {
      const values = height_mm === 65
        ? presets.find((p) => p.id === "test-fit-65mm")!.values
        : { grid_x: 1, grid_y: 1, height_mode: "total mm", height_mm };
      const result = await renderToStl({
        source: applyParamOverrides(source, params, values),
        fetchLibFile: async (rel) => {
          try { return await readFile(path.join(ROOT, "libs", rel), "utf8"); }
          catch { return null; }
        },
      });
      expect(result.ok, result.errorMessage).toBe(true);
      expect(result.stderr.filter((s) => /ERROR/.test(s))).toEqual([]);
      const triangles = parseStlTriangles(result.stl!);
      expect(triangles.length).toBeGreaterThan(0);
      expect(isWatertight(triangles)).toBe(true);
      expect(connectedComponentCount(triangles)).toBe(1);
      let low = Infinity;
      let high = -Infinity;
      for (const { vertices } of triangles) {
        for (const vertex of vertices) {
          low = Math.min(low, vertex[2]);
          high = Math.max(high, vertex[2]);
        }
      }
      expect(Math.abs(low), "base must sit on the bed").toBeLessThanOrEqual(0.01);
      expect(Math.abs(high - low - height_mm), "lip-inclusive Z extent").toBeLessThanOrEqual(0.1);
    }, 300_000);
  }
});
