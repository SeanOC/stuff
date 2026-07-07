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
