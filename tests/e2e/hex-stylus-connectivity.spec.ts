import { expect, test } from "@playwright/test";
import {
  RENDER_READY_TIMEOUT_MS,
  waitForRenderReady,
  waitForStale,
} from "./support/render";

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

  // The detail page auto-fires the first render on mount with default
  // params (st-2y4); wait it out before touching anything. Rendering is
  // manual now (pst-vfp) — editing hex_width only marks the preview
  // stale, so dial in the operator's value and click Re-render to apply
  // it. (The old idle-Enter path no longer reaches this render: the
  // mount fire has already left the idle state that Enter is gated on.)
  await waitForRenderReady(page);
  await page.locator("#param-hex_width").fill("9");
  await waitForStale(page, true);
  await page.getByTestId("stale-rerender").click();

  // Ready state: the stat strip shows per-axis dimensions. Lying flat,
  // Z is the hex across flats — exactly the 9mm we dialed in; X is the
  // 90mm default length. A shattered fin-only mesh (the st-7x7 failure
  // mode: ~6.3 × 1 × 3.6 mm) can't satisfy this. toContainText polls
  // until the re-render lands (the default-param mount render's
  // 8mm dims don't match the pattern, so it can't satisfy early), on a
  // render-sized budget so a slow CGAL hull doesn't time it out.
  const dims = page.getByTestId("stat-strip-dimensions");
  await expect(dims).toContainText(/90\.\d × 10\.\d × 9\.0 mm/, {
    timeout: RENDER_READY_TIMEOUT_MS,
  });

  // And the render must not have taken the error path.
  await expect(page.getByTestId("error-strip")).toHaveAttribute("aria-hidden", "true");
});
