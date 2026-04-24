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
