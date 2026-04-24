import { expect, test } from "@playwright/test";

// Guard for the retina STL-preview bug: renderer.setSize(w, h, false)
// leaves the canvas without a CSS size, so on devicePixelRatio > 1 it
// renders at its attribute size (w*DPR × h*DPR CSS pixels), overflows
// the viewer, and gets clipped by overflow:hidden to a blank region.
// DPR=1 headless environments can't see this, so force DPR=2 here.

test.use({ deviceScaleFactor: 2 });

test("STL preview canvas fits the container on retina (DPR=2)", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");
  // Phase 2b (st-psn): Enter kicks off the first render from idle.
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
    timeout: 60_000,
  });

  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();

  const dims = await canvas.evaluate((el: HTMLCanvasElement) => {
    const parent = el.parentElement!;
    return {
      canvasCssW: el.clientWidth,
      canvasCssH: el.clientHeight,
      parentW: parent.clientWidth,
      parentH: parent.clientHeight,
      backingW: el.width,
      backingH: el.height,
      dpr: window.devicePixelRatio,
    };
  });

  expect(dims.dpr, "Playwright failed to inject DPR=2").toBe(2);

  // The canvas's CSS size must not exceed its container; otherwise the
  // viewer clips it and the mesh sits outside the visible region.
  expect(dims.canvasCssW).toBeLessThanOrEqual(dims.parentW);
  expect(dims.canvasCssH).toBeLessThanOrEqual(dims.parentH);

  // And the backing store should be CSS-size × DPR, which is how three.js
  // renders at full retina sharpness without overflowing.
  expect(dims.backingW).toBe(dims.canvasCssW * dims.dpr);
  expect(dims.backingH).toBe(dims.canvasCssH * dims.dpr);
});
