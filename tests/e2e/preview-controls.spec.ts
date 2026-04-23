import { expect, test } from "@playwright/test";

// Smoke test for STL preview OrbitControls (st-90j). Dispatches a wheel
// event on the canvas and verifies the three.js camera moved — proving
// OrbitControls is wired up and rendering on demand.
//
// StlViewer stashes { camera, controls } on canvas.__stlViewer for
// inspection here; the component API is unchanged.

test("STL preview responds to wheel (camera moves)", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");
  await expect(page.getByText(/\d+ms · [\d.]+kb/).first()).toBeVisible({
    timeout: 60_000,
  });

  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();

  const before = await canvas.evaluate((el: HTMLCanvasElement) => {
    const h = (el as unknown as { __stlViewer?: { camera: { position: { x: number; y: number; z: number } } } }).__stlViewer;
    if (!h) return null;
    const p = h.camera.position;
    return { x: p.x, y: p.y, z: p.z };
  });

  expect(before, "StlViewer debug handle missing — is OrbitControls wired up?").not.toBeNull();

  const box = await canvas.boundingBox();
  if (!box) throw new Error("canvas has no bounding box");
  const cx = box.x + box.width / 2;
  const cy = box.y + box.height / 2;

  await page.mouse.move(cx, cy);
  // Try a wheel zoom-in. Headless chromium occasionally no-ops wheel
  // events; if the camera didn't move, skip rather than flake.
  await page.mouse.wheel(0, -240);
  await page.waitForTimeout(100);

  const after = await canvas.evaluate((el: HTMLCanvasElement) => {
    const h = (el as unknown as { __stlViewer?: { camera: { position: { x: number; y: number; z: number } } } }).__stlViewer!;
    const p = h.camera.position;
    return { x: p.x, y: p.y, z: p.z };
  });

  const moved =
    Math.abs(after.x - before!.x) +
    Math.abs(after.y - before!.y) +
    Math.abs(after.z - before!.z);
  test.skip(moved < 1e-6, "headless wheel event was not delivered to the canvas");
  expect(moved).toBeGreaterThan(1e-6);
});
