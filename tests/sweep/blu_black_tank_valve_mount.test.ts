import { describe, expect, it } from "vitest";
import { isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";
import { renderSweepCase, sweepModel } from "./runner";

sweepModel("blu_black_tank_valve_mount");

// _rbox radius-boundary regression (pst-a9f). The single-axis sweep can't
// reach saddle_w × edge_round_r together, and this model's default
// saddle_w (15) never hits 2*r == saddle_w on the edge_round_r axis. When
// 2*r >= the smaller edge, the old _rbox inset collapsed the inner polygon
// to zero area and the part rendered empty. Cover the joint boundary and
// past it explicitly.
describe("blu_black_tank_valve_mount — _rbox radius boundary", () => {
  for (const [saddle_w, edge_round_r] of [
    [10, 5], // 2*r == saddle_w (codex reproducer)
    [5, 5], // 2*r  > saddle_w
  ] as const) {
    it(`cap_left renders non-empty at saddle_w=${saddle_w}, edge_round_r=${edge_round_r}`, async () => {
      const res = await renderSweepCase("blu_black_tank_valve_mount", {
        part: "cap_left",
        saddle_w,
        edge_round_r,
      });
      expect(res.ok, `render failed: ${res.errorMessage ?? "?"}`).toBe(true);
      const tris = parseStlTriangles(res.stl!);
      expect(tris.length, "empty mesh").toBeGreaterThan(0);
      expect(isWatertight(tris), "mesh is not watertight").toBe(true);
    }, 300_000);
  }
});
