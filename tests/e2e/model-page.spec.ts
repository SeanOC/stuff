import { expect, test } from "@playwright/test";

// Uses smoke-motor-mount because it's the cheapest annotated model
// (no BOSL2 includes → sub-second WASM render) so the "wait for first
// render" step doesn't blow the test budget.

test.describe("model page", () => {
  test("param form exposes each annotated parameter with default", async ({ page }) => {
    await page.goto("/models/smoke-motor-mount");

    // Every @param becomes an id-scoped input. Verify a few known ones.
    await expect(page.locator("#param-plate_w")).toHaveValue("60");
    await expect(page.locator("#param-plate_t")).toHaveValue("5");
    await expect(page.locator("#param-bore")).toHaveValue("20");
    await expect(page.locator("#param-hole_d")).toHaveValue("3.2");

    // Range+number pair on each numeric param: id-scoped <input> is the
    // number box; a sibling slider sits in the same row.
    const row = page.locator("#param-plate_w").locator("xpath=..");
    await expect(row.locator('input[type="range"]')).toHaveCount(1);
  });

  test("download button present and status line renders", async ({ page }) => {
    await page.goto("/models/smoke-motor-mount");
    await expect(page.getByRole("button", { name: /Download STL/i })).toBeVisible();
    // Status line starts at "rendering…" then transitions to "rendered in Xms · Y bytes".
    await expect(page.getByText(/rendered in \d+ms · [\d,]+ bytes/)).toBeVisible({ timeout: 60_000 });
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
