import { describe, expect, it } from "vitest";
import { isWatertight, parseStlTriangles } from "@/lib/wasm/stl-analysis";
import { renderSweepCase, sweepModel } from "./runner";

sweepModel("blu_flow_meter_mount_80mm");

// _rbox radius-boundary regression (pst-a9f). This model's default
// saddle_w is 10, so edge_round_r=5 alone lands on 2*r == saddle_w — the
// exact boundary where the old _rbox inset collapsed the inner polygon to
// zero area and the cap rendered empty. Cover the boundary and past it.
describe("blu_flow_meter_mount_80mm — _rbox radius boundary", () => {
  for (const [saddle_w, edge_round_r] of [
    [10, 5], // 2*r == saddle_w (codex reproducer)
    [5, 5], // 2*r  > saddle_w
  ] as const) {
    it(`cap renders non-empty at saddle_w=${saddle_w}, edge_round_r=${edge_round_r}`, async () => {
      const res = await renderSweepCase("blu_flow_meter_mount_80mm", {
        part: "cap",
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
