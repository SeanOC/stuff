import { expect, test } from "@playwright/test";

// Viewer state contracts. Phase 2b (st-psn) made idle/loading/ready/
// error observable; phase-3c-era revert (st-2y4) flipped the default
// to auto-fire on mount, so a cold model page goes straight through
// idle → loading → ready without a key press. The press-⏎ hint UI
// stays in the tree as the error-recovery path; it's just not the
// default empty state anymore.

test.describe("ViewerChrome states", () => {
  test("cold page load auto-fires the render — no press-⏎ hint", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    // The hint should never appear on a healthy cold load. It's kept in
    // the tree for the error-recovery path (which is exercised by
    // tests/e2e/error-state.spec.ts), but on a fresh valid model the
    // mount effect fires refresh() before React paints idle.
    await expect(page.getByTestId("press-enter-hint")).toHaveCount(0);

    // The viewer transitions straight through loading to ready and the
    // stat strip ends up showing dimensions.
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
      timeout: 60_000,
    });

    // Download enables once state.kind === "ready".
    const download = page.getByRole("button", { name: /Download STL/i });
    await expect(download).toBeVisible();
    await expect(download).toBeEnabled();
  });

  test("axes indicator tracks live camera orbit, not just preset clicks (st-oc3)", async ({
    page,
  }) => {
    await page.goto("/models/popcorn-kernel");
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
      timeout: 60_000,
    });

    // Capture the X-axis line endpoints at the current preset.
    const xLine = page.locator('[data-testid="axes-indicator"] g[data-axis="x"] line');
    await expect(xLine).toBeVisible();
    const beforeX = await xLine.getAttribute("x2");
    const beforeY = await xLine.getAttribute("y2");
    expect(beforeX).not.toBeNull();

    // Drag across the viewer canvas to orbit the camera. OrbitControls
    // hooks mousedown/move/up on the canvas; dispatching to the
    // [data-testid="stl-viewer"] container hits the canvas (the renderer
    // domElement is appended inside it). A 200px diagonal drag is
    // enough to pull the orientation off any of the preset tangents.
    const viewer = page.getByTestId("stl-viewer");
    const box = await viewer.boundingBox();
    if (!box) throw new Error("viewer bounding box missing");
    const cx = box.x + box.width / 2;
    const cy = box.y + box.height / 2;
    await page.mouse.move(cx, cy);
    await page.mouse.down();
    await page.mouse.move(cx + 160, cy - 120, { steps: 20 });
    await page.mouse.up();

    // The X-axis endpoint should have moved. Polling via toPass gives
    // React a frame or two to flush the setAxes state update from the
    // OrbitControls 'change' handler.
    await expect
      .poll(async () => ({
        x: await xLine.getAttribute("x2"),
        y: await xLine.getAttribute("y2"),
      }))
      .not.toEqual({ x: beforeX, y: beforeY });
  });

  test("axes indicator snaps with view-preset tab click (st-oc3)", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
      timeout: 60_000,
    });

    const xLine = page.locator('[data-testid="axes-indicator"] g[data-axis="x"] line');
    await expect(xLine).toBeVisible();
    const before = {
      x: await xLine.getAttribute("x2"),
      y: await xLine.getAttribute("y2"),
    };

    // Click the Top preset. The tab flips aria-selected, and the
    // camera snaps, which routes through OrbitControls.update() →
    // 'change' → onCameraChange → indicator redraw. Both the preset
    // attribute and the X-axis line endpoint change.
    await page.getByRole("tab", { name: /top/i }).click();
    await expect(page.getByTestId("axes-indicator")).toHaveAttribute(
      "data-preset",
      "top",
    );
    await expect
      .poll(async () => ({
        x: await xLine.getAttribute("x2"),
        y: await xLine.getAttribute("y2"),
      }))
      .not.toEqual(before);
  });

  test("Enter still triggers a re-render (kept for the error-retry path)", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    // Wait for the initial auto-render so the renderer is in a sane
    // state; without this, the focused Enter could race the mount.
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
      timeout: 60_000,
    });

    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");

    // After Enter, the viewer cycles back through loading and lands
    // at ready again. The dimensions stat strip remains the ready-
    // state marker.
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({
      timeout: 60_000,
    });
  });
});
