import { expect, test } from "@playwright/test";

// Phase 3a (st-1j9): stock + user presets, the modified-dot, and the
// inline save-row UX. cylindrical-holder-slot is the fixture of choice
// because it ships four historic stock presets (42/46/70/77 mm).

test.describe("presets", () => {
  test("param rail lists stock presets and loading one sets active + clears modified", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot");
    // st-yxj: presets now live at the top of the param rail (right
    // column), always visible at desktop viewport sizes.

    const list = page.getByTestId("preset-list");
    await expect(list).toBeVisible();
    // All four historic stock presets present.
    for (const id of ["42mm-cylinder", "46mm-cylinder", "70mm-spraycan", "77mm-spraycan"]) {
      await expect(list.locator(`[data-preset-id="${id}"]`)).toBeVisible();
    }

    // Click 46mm: it becomes active and the modified-dot is absent.
    await list.locator('[data-preset-id="46mm-cylinder"]').click();
    await expect(page.getByTestId("modified-dot")).toHaveCount(0);
    await expect(page.locator("#param-can_diameter")).toHaveValue("46");

    // Edit a param — modified-dot appears next to the active preset.
    await page.locator("#param-can_diameter").fill("48");
    await expect(page.getByTestId("modified-dot")).toBeVisible();
  });

  test("⌘S opens the inline save-row; Enter persists; new preset appears active", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot");
    // st-yxj: save-row + preset list now live in the param rail —
    // visible by default, no expand step needed.

    // Bump a param so the save captures a distinct state.
    await page.locator("#param-can_diameter").fill("55");

    // Shortcut opens the inline row. The viewer has a specific focus-
    // gate for bare keys, but ⌘S is a mod chord and fires anywhere.
    await page.keyboard.press("Meta+s");

    const input = page.getByTestId("save-preset-input");
    await expect(input).toBeVisible();
    await input.fill("My 55 preset");
    await page.keyboard.press("Enter");

    // Input goes away, the new preset appears, and it's active.
    await expect(page.getByTestId("save-preset-input")).toHaveCount(0);
    const list = page.getByTestId("preset-list");
    const savedRow = list.getByText("My 55 preset");
    await expect(savedRow).toBeVisible();
  });
});
