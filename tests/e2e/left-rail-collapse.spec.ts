import { expect, test } from "@playwright/test";

// st-j98: the detail page's left metadata rail defaults to collapsed
// at ≥1200px, with a chevron button to toggle. State persists via
// localStorage so returning visitors keep whichever mode they picked.
// st-yxj moved presets out of this rail and into the param rail; the
// left rail now contains source path, render log, and warnings — we
// use the "Render log" label as the visibility marker.

test.describe("left rail collapse (detail page)", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("collapsed by default; chevron expands and collapses", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");

    // Default: collapsed. The collapsed-mode chevron is visible; the
    // desktop metadata content is removed from the DOM at xl+ when
    // collapsed. (The mobile-disclosure copy of the same content
    // exists in the tree but is hidden by `min-[1200px]:hidden`.)
    const expandBtn = page.getByRole("button", { name: /Expand left rail/i });
    await expect(expandBtn).toBeVisible();
    // Only the desktop tree's content is visible at xl+. Filter by
    // visibility so the mobile copy (always display:none here) doesn't
    // confuse strict-mode matching.
    const railContent = page.getByTestId("detail-left-rail-content").locator("visible=true");
    await expect(railContent).toHaveCount(0);

    // Click expand → metadata content visible, collapse chevron available.
    await expandBtn.click();
    await expect(railContent).toHaveCount(1);
    const collapseBtn = page.getByRole("button", { name: /Collapse left rail/i });
    await expect(collapseBtn).toBeVisible();

    // Click collapse → metadata content hidden again.
    await collapseBtn.click();
    await expect(railContent).toHaveCount(0);
    await expect(expandBtn).toBeVisible();
  });
});
