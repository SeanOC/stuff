// Geometry baselines measured from unmodified HomeRacker at the pinned commit.
// These checks cover every annotated preset, including the twenty-solid plate.
import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { applyParamOverrides, defaultsOf, parseScadParams } from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import { connectedComponentCount, isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";
import reference from "../fixtures/homeracker-reference.json";

const ROOT = path.resolve(__dirname, "../..");
type Stem = keyof typeof reference.models;
type Reference = { bbox_mm: number[]; volume_mm3: number; solids: number };

export function checkHomeRackerPresets(stem: Stem): void {
  const source = readFileSync(path.join(ROOT, "models", `${stem}.scad`), "utf8");
  const { params, presets } = parseScadParams(source);
  const baselines: Record<string, Reference> = reference.models[stem];
  describe(`${stem} upstream preset geometry`, () => {
    it("has a baseline for exactly every published preset", () => {
      expect(presets.map((p) => p.id).sort()).toEqual(Object.keys(baselines).sort());
    });
    for (const preset of presets) {
      it(preset.id, async () => {
        const ref = baselines[preset.id];
        const values = { ...defaultsOf(params), ...preset.values };
        const result = await renderToStl({
          source: applyParamOverrides(source, params, values),
          fetchLibFile: async (rel) => {
            try { return await readFile(path.join(ROOT, "libs", rel), "utf8"); }
            catch { return null; }
          },
        });
        expect(result.ok, result.errorMessage).toBe(true);
        expect(result.stderr.filter((s) => /WARNING|ERROR/.test(s))).toEqual([]);
        const tris = parseStlTriangles(result.stl!);
        expect(isWatertight(tris)).toBe(true);
        expect(connectedComponentCount(tris)).toBe(ref.solids);
        const low = [Infinity, Infinity, Infinity];
        const high = [-Infinity, -Infinity, -Infinity];
        let signedVolume = 0;
        for (const { vertices: [a, b, c] } of tris) {
          for (const v of [a, b, c]) {
            for (let axis = 0; axis < 3; axis++) {
              low[axis] = Math.min(low[axis], v[axis]);
              high[axis] = Math.max(high[axis], v[axis]);
            }
          }
          signedVolume += (a[0] * (b[1]*c[2] - b[2]*c[1])
            + a[1] * (b[2]*c[0] - b[0]*c[2])
            + a[2] * (b[0]*c[1] - b[1]*c[0])) / 6;
        }
        for (let axis = 0; axis < 3; axis++) {
          expect(Math.abs(high[axis] - low[axis] - ref.bbox_mm[axis])).toBeLessThanOrEqual(0.01);
        }
        expect(Math.abs(Math.abs(signedVolume) / ref.volume_mm3 - 1)).toBeLessThanOrEqual(0.001);
      }, 300_000);
    }
  });
}
