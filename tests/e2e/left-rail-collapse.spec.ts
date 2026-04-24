import { expect, test } from "@playwright/test";

// st-j98: the detail page's left rail (source / presets / render log)
// defaults to collapsed at ≥1200px, with a chevron button to toggle.
// Collapse state persists via localStorage so returning visitors keep
// whichever mode they picked.

test.describe("left rail collapse (detail page)", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("collapsed by default; chevron expands and collapses", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    // Default: collapsed. The collapsed-mode chevron is visible and
    // the preset list is hidden (removed from the tree at xl+).
    const expandBtn = page.getByRole("button", { name: /Expand left rail/i });
    await expect(expandBtn).toBeVisible();
    await expect(page.getByTestId("preset-list")).toBeHidden();

    // Click expand → preset list visible, collapse chevron available.
    await expandBtn.click();
    await expect(page.getByTestId("preset-list")).toBeVisible();
    const collapseBtn = page.getByRole("button", { name: /Collapse left rail/i });
    await expect(collapseBtn).toBeVisible();

    // Click collapse → preset list hidden again.
    await collapseBtn.click();
    await expect(page.getByTestId("preset-list")).toBeHidden();
    await expect(expandBtn).toBeVisible();
  });
});
