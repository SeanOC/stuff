import { expect, test } from "@playwright/test";
import { waitForRenderReady } from "./support/render";

// st-7x7 operator repro, pinned end-to-end: the hex stylus at
// hex_width=9 must render intact in the real site preview. Before the
// fix, CGAL's randomized hull inside the wasm engine could drop the
// hulled body (logging ERROR but exiting 0), and the preview showed
// only the breakaway fin + ribs as disjoint pieces. Two layers now
// prevent that — the model's hull spheres are in generic position, and
// lib/wasm/render.ts refuses exit-0-with-ERROR renders — so the
// preview must reach the ready state with the stylus's real bbox, and
// the error strip must stay hidden.

test("hex stylus renders intact at hex_width=9 in the live preview", async ({ page }) => {
  await page.goto("/models/lcd-stylus-hex-8mm");

  // Set the operator's exact param before the first render.
  await page.locator("#param-hex_width").fill("9");

  // Kick off the render via the idle-state Enter affordance (st-psn).
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");

  // Ready state: the stat strip shows per-axis dimensions. Lying flat,
  // Z is the hex across flats — exactly the 9mm we dialed in; X is the
  // 90mm default length. A shattered fin-only mesh (the st-7x7 failure
  // mode: ~6.3 × 1 × 3.6 mm) can't satisfy this.
  await waitForRenderReady(page);
  const dims = page.getByTestId("stat-strip-dimensions");
  await expect(dims).toContainText(/90\.\d × 10\.\d × 9\.0 mm/);

  // And the render must not have taken the error path.
  await expect(page.getByTestId("error-strip")).toHaveAttribute("aria-hidden", "true");
});
