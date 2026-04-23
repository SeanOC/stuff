import { expect, test } from "@playwright/test";

// Phase 2b (st-psn): the idle/loading/ready states are observable UI
// contracts, not just internal machinery. Empty state shows a
// "press ⏎ to render" hint and disables Download STL. Pressing Enter
// transitions out of idle. Once a render completes, the stat strip
// leads with the model's per-axis dimensions.

test.describe("ViewerChrome states", () => {
  test("empty state shows press-enter hint and disables Download STL", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    // The hint sits inside the viewer placeholder, visible immediately
    // on mount because nothing has triggered the first render yet.
    await expect(page.getByTestId("press-enter-hint")).toBeVisible();
    await expect(page.getByTestId("stat-strip-status")).toHaveText(/press/i);

    // Download button exists (rendered by DetailPage's DownloadButton)
    // but is disabled until state.kind === 'ready'.
    const download = page.getByRole("button", { name: /Download STL/i });
    await expect(download).toBeVisible();
    await expect(download).toBeDisabled();
  });

  test("pressing Enter on the viewer kicks off the first render", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    await expect(page.getByTestId("press-enter-hint")).toBeVisible();

    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");

    // Idle → loading → ready. The hint disappears once we leave idle.
    await expect(page.getByTestId("press-enter-hint")).toBeHidden({ timeout: 60_000 });

    // Ready: the stat strip has dimensions and the Download button enables.
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByRole("button", { name: /Download STL/i })).toBeEnabled();
  });
});
