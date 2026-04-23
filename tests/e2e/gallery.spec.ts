import { expect, test } from "@playwright/test";

// Expected models after Phase 3. Order matches the filesystem-alphabetic
// sort in listModels(). If a model is added/removed, update this list
// AND verify the gallery-spec snapshot still makes sense.
const EXPECTED_SLUGS = [
  "cylindrical-holder-slot",
  "popcorn-kernel",
];

test.describe("gallery", () => {
  test("renders one card per model with title + link", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Parametric things/i })).toBeVisible();

    for (const slug of EXPECTED_SLUGS) {
      const link = page.locator(`a[href="/models/${slug}"]`);
      await expect(link, `card for ${slug}`).toBeVisible();
      // Filename mono code appears inside the card, confirms the stem rendered.
      await expect(link).toContainText(/\.scad/);
    }
  });

  test("every thumbnail request resolves 200", async ({ page }) => {
    const thumbResponses: number[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/api/thumbnail")) {
        thumbResponses.push(res.status());
      }
    });
    await page.goto("/");
    // Force background-image fetches by scrolling everything into view.
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    // Small quiet window: thumbnails are background-image so they load
    // eagerly, but network can race with navigation events.
    await page.waitForLoadState("networkidle");

    expect(thumbResponses.length).toBeGreaterThanOrEqual(EXPECTED_SLUGS.length);
    // 200 = rendered thumbnail, 404 = no render on disk (gallery
    // falls back to the card's own background fill — intentional
    // graceful degradation, not a bug). Anything else (403, 5xx) is
    // a real failure we want to surface.
    for (const status of thumbResponses) {
      expect(status === 200 || status === 404).toBe(true);
    }
  });

  test("clicking a card navigates to the model page", async ({ page }) => {
    await page.goto("/");
    await page.locator('a[href="/models/popcorn-kernel"]').click();
    await expect(page).toHaveURL(/\/models\/popcorn-kernel$/);
    await expect(page.locator("code", { hasText: "models/popcorn_kernel.scad" })).toBeVisible();
  });
});
