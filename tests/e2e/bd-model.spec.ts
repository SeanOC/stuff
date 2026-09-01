import { expect, test } from "@playwright/test";

// End-to-end for the build123d preset flow (bead pst-0um9): the bd
// detail page loads, its baked GLB renders, and the preset STL
// downloads.
//
// Opt-in. The whole feature is gated on BD_MODELS_ENABLED, and the GLB
// viewer + download need the presets baked into build123d/baked/. So
// this spec only runs when a run explicitly enables it:
//
//   bash scripts/vendor-libs.sh                     # once
//   BD_MODELS_ENABLED=1 bash scripts/bake-bd-presets.sh
//   BD_MODELS_ENABLED=1 npm run test:e2e -- bd-model
//
// playwright.config.ts passes BD_MODELS_ENABLED through to the web
// server, so the same var both un-skips this spec and un-hides the bd
// pages. Unset in CI → the pages stay hidden and this spec skips,
// leaving the required e2e check untouched.
test.skip(
  process.env.BD_MODELS_ENABLED !== "1",
  "build123d preset flow is opt-in (set BD_MODELS_ENABLED=1 and bake first)",
);

const SLUG = "holder-spray-can";

test("bd model page loads, GLB renders upright, and the preset STL downloads", async ({
  page,
}) => {
  await page.goto(`/models/${SLUG}`);

  // The bd detail shell, not the SCAD DetailPage.
  await expect(page.getByTestId("bd-detail-root")).toBeVisible();
  await expect(page.getByTestId("bd-presets-only-notice")).toBeVisible();
  await expect(page.getByTestId("bd-preset-spray_can")).toBeVisible();

  // GLB load populates the bbox strip. data-glb-size = "x,y,z" in the
  // GLB's own units (metres, from OCP). Orientation assertion: pin the
  // known-good upright envelope for this preset (collar h=60mm → Y-up,
  // back-plate depth pushing Z past it). A double -90°X rotation would
  // swap Y and Z, dropping the ring's 60mm height into Z — which the
  // `z > 0.062` bound below catches. We assert the shipped envelope
  // rather than "Y is tallest" because for this near-cubic holder the
  // back-plate depth (~64mm) legitimately exceeds the collar height.
  const sizeEl = page.getByTestId("bd-glb-size");
  await expect(sizeEl).toBeVisible({ timeout: 30_000 });
  const raw = await sizeEl.getAttribute("data-glb-size");
  expect(raw).toBeTruthy();
  const [x, y, z] = raw!.split(",").map(Number);
  expect(Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)).toBe(true);
  // Ring height (60mm collar) maps to Y-up; depth incl. the back plate
  // (~64mm) is the largest axis. A double-rotation swap would put the
  // 60mm height into Z (< 0.062) and fail the second bound.
  expect(y).toBeCloseTo(0.06, 2);
  expect(z).toBeGreaterThan(0.062);

  // Orientation compass parity with the SCAD viewer (pst-6ram): the same
  // axes indicator renders, and by GLB-load time it has switched off the
  // static fallback onto the live camera projection (X/Y/Z lines present).
  const compass = page.getByTestId("axes-indicator");
  await expect(compass).toBeVisible();
  await expect(compass.locator('g[data-axis="x"] line')).toBeVisible();
  await expect(compass.locator('g[data-axis="y"] line')).toBeVisible();
  await expect(compass.locator('g[data-axis="z"] line')).toBeVisible();

  // Download the baked preset STL.
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("bd-download-stl").click(),
  ]);
  expect(download.suggestedFilename()).toBe(`${SLUG}-spray_can.stl`);
  const path = await download.path();
  expect(path).toBeTruthy();
  const { statSync } = await import("node:fs");
  expect(statSync(path!).size).toBeGreaterThan(1000);
});
