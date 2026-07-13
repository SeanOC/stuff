import { expect, test } from "@playwright/test";
import {
  connectedComponentCount,
  isWatertight,
  parseStlTriangles,
} from "../../lib/wasm/stl-analysis";

// Exercises the full export path. The download → file-read round-trip
// is what catches "button click does nothing" and "blob empty" regressions
// — the preview-rerender test doesn't cover the API export route at all.

test("Download STL produces a non-empty STL file", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  // Phase 2b (st-psn): the viewer starts idle and the Download STL
  // button is disabled until a render completes. Press Enter to kick
  // the first render, wait for the log entry, and only then assert
  // the button is enabled.
  const button = page.getByRole("button", { name: /Download STL/i });
  await expect(button).toBeDisabled();

  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({ timeout: 60_000 });
  await expect(button).toBeEnabled();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    button.click(),
  ]);

  expect(download.suggestedFilename()).toBe("popcorn_kernel.stl");

  const path = await download.path();
  expect(path).toBeTruthy();
  const { readFileSync, statSync } = await import("node:fs");
  const size = statSync(path!).size;
  expect(size).toBeGreaterThan(1000);

  const head = readFileSync(path!, "utf8").slice(0, 32);
  expect(head.startsWith("solid")).toBe(true);
});

// st-zph pinned this route against the import()-asset silent-drop bug;
// st-82o then remodeled the blower mount as native CSG, which is also
// the perf fix: the import()+Manifold union took ~23s per export and
// pushed cold serverless starts past the gateway timeout (HTTP 504).
// The test stays as the end-to-end guard on the heaviest model's
// download path: 200, one watertight solid, full bracket extent —
// and the tightened timeout keeps the render from creeping back
// toward gateway-timeout territory (native CSG renders sub-second;
// the budget is wasm init + CI slack).
test("export route serves the ego blower mount fast and complete", async ({ baseURL }) => {
  test.setTimeout(120_000);
  if (!baseURL) throw new Error("baseURL missing");

  const res = await fetch(`${baseURL}/api/export`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model: "models/ego_lb6500_blower_mount.scad", params: {} }),
  });
  expect(res.status, await res.clone().text().catch(() => "")).toBe(200);

  const tris = parseStlTriangles(new Uint8Array(await res.arrayBuffer()));
  expect(isWatertight(tris)).toBe(true);
  expect(connectedComponentCount(tris)).toBe(1);

  // PRINT_ANCHOR_BBOX = [138.5, 93.5, 166.5]. A dropped bracket body
  // (the st-zph failure shape) leaves only the backer — the Z extent
  // is the tell.
  let maxZ = -Infinity, minZ = Infinity;
  for (const t of tris) {
    for (const v of t.vertices) {
      if (v[2] > maxZ) maxZ = v[2];
      if (v[2] < minZ) minZ = v[2];
    }
  }
  expect(maxZ - minZ).toBeCloseTo(166.5, 0);
});

// Import()-asset download pipeline (st-zph class; pinned per pst-3m2,
// closes GT st-0t8). The webapp download path once silently dropped
// import()ed meshes: the asset fetcher was missing, OpenSCAD only
// WARNs on an unreadable import(), and the route served a fragmented
// STL while CI's native export looked fine. renderToStl now hard-fails
// on missing assets and the route supplies assetFetcherFor() — this
// test drives the whole chain through the real HTTP route with a tiny
// frozen fixture (binary STL cube + native cuboid union) so it stays
// fast. The imported mesh alone cannot reach x > 20 and the native
// cuboid alone cannot span 20mm in z, so the asserted 35 x 20 x 20
// bbox proves BOTH halves made it into one watertight solid.
test("export route delivers import()ed binary assets into the download", async ({ baseURL }) => {
  if (!baseURL) throw new Error("baseURL missing");

  const res = await fetch(`${baseURL}/api/export`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model: "tests/fixtures/import_asset.scad", params: {} }),
  });
  expect(res.status, await res.clone().text().catch(() => "")).toBe(200);

  const tris = parseStlTriangles(new Uint8Array(await res.arrayBuffer()));
  expect(isWatertight(tris)).toBe(true);
  expect(connectedComponentCount(tris)).toBe(1);

  let min = [Infinity, Infinity, Infinity];
  let max = [-Infinity, -Infinity, -Infinity];
  for (const t of tris) {
    for (const v of t.vertices) {
      for (let k = 0; k < 3; k++) {
        if (v[k] < min[k]) min[k] = v[k];
        if (v[k] > max[k]) max[k] = v[k];
      }
    }
  }
  expect(max[0] - min[0]).toBeCloseTo(35, 1); // mesh (20) + native reach (15)
  expect(max[1] - min[1]).toBeCloseTo(20, 1); // mesh-only extent
  expect(max[2] - min[2]).toBeCloseTo(20, 1); // mesh-only extent — cuboid alone spans 10
});

// The real import()-based model on the same route (pst-3m2 acceptance
// criterion): ego_powerhead_mount unions the operator's 7,676-triangle
// mesh with screw-hole plugs and six openGrid snaps. A dropped import
// leaves only the snaps+plugs stack (~21.8mm tall) — the Z extent is
// the tell, same shape as the blower's st-zph guard above. Budget: the
// wasm render takes ~28s locally; the timeout covers wasm init + CI
// slack without letting the route creep toward the 120s serverless
// maxDuration.
test("export route serves the import()-based powerhead mount complete", async ({ baseURL }) => {
  test.setTimeout(240_000);
  if (!baseURL) throw new Error("baseURL missing");

  const res = await fetch(`${baseURL}/api/export`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model: "models/ego_powerhead_mount.scad", params: {} }),
  });
  expect(res.status, await res.clone().text().catch(() => "")).toBe(200);

  const tris = parseStlTriangles(new Uint8Array(await res.arrayBuffer()));
  expect(isWatertight(tris)).toBe(true);
  expect(connectedComponentCount(tris)).toBe(1);

  // PRINT_ANCHOR_BBOX = [56, 110, 141.78].
  let maxZ = -Infinity, minZ = Infinity;
  for (const t of tris) {
    for (const v of t.vertices) {
      if (v[2] > maxZ) maxZ = v[2];
      if (v[2] < minZ) minZ = v[2];
    }
  }
  expect(maxZ - minZ).toBeCloseTo(141.78, 1);
});
