import { expect, test } from "@playwright/test";

// st-yxj: below 1200px the metadata pane (left rail content)
// collapses to a single disclosure row above the viewer. Default
// closed so visitors land on the viewer + params, not a wall of
// metadata. Tap the summary to expand.

test.describe("mobile metadata disclosure", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("disclosure default closed; tap to expand", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    const disclosure = page.getByTestId("metadata-mobile-disclosure");
    await expect(disclosure).toBeVisible();
    // <details> not open by default.
    await expect(disclosure).not.toHaveAttribute("open", "");

    // Tap the summary → opens.
    await disclosure.locator("summary").click();
    await expect(disclosure).toHaveAttribute("open", "");

    // Tap again → closes.
    await disclosure.locator("summary").click();
    await expect(disclosure).not.toHaveAttribute("open", "");
  });

  test("presets live in the param rail at mobile width too", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot");
    // Param rail stacks below the viewer at <1200px; the preset list
    // is rendered inline at the top of the param column.
    await expect(page.getByTestId("preset-list")).toBeVisible();
  });
});
