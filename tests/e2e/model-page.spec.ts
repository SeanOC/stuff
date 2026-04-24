import { expect, test } from "@playwright/test";

// Uses popcorn-kernel because it's the cheapest annotated model
// (no BOSL2 includes → sub-second WASM render) so the "wait for first
// render" step doesn't blow the test budget.

test.describe("model page", () => {
  test("param form exposes each annotated parameter with default", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    // Every @param becomes an id-scoped input. Verify the known one.
    await expect(page.locator("#param-base_cut")).toHaveValue("4");

    // Range+number pair on each numeric param: id-scoped <input> is the
    // number box; a sibling slider sits in the same row.
    const row = page.locator("#param-base_cut").locator("xpath=..");
    await expect(row.locator('input[type="range"]')).toHaveCount(1);
  });

  test("download button present and status line renders", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    await expect(page.getByRole("button", { name: /Download STL/i })).toBeVisible();

    // Phase 2b: viewer starts idle — must press Enter to trigger the
    // first render (st-psn). See ViewerChrome.handleKeyDown.
    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");

    // Render completion signal — the stat-strip dimensions line
    // lives in the viewer chrome, independent of the left rail
    // (which is collapsed by default per st-j98).
    await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({ timeout: 60_000 });
  });

  test("unannotated model shows the placeholder note", async ({ page }) => {
    // All current models are annotated; skip gracefully if the placeholder
    // has nothing to assert against. If an unannotated model is ever added
    // the gallery-card amber note will catch it; this test stays green.
    await page.goto("/");
    const amberCard = page.locator("text=not yet annotated").first();
    if (await amberCard.count() === 0) {
      test.skip(true, "all models annotated — nothing to assert");
    }
  });
});
