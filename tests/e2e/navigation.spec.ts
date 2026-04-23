import { expect, test } from "@playwright/test";

test("gallery ↔ model page round-trip via link + back button", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Parametric things/i })).toBeVisible();

  await page.locator('a[href="/models/popcorn-kernel"]').click();
  await expect(page).toHaveURL(/\/models\/popcorn-kernel$/);
  await expect(page.getByRole("link", { name: /all models/i })).toBeVisible();

  // "← all models" link back to gallery.
  await page.getByRole("link", { name: /all models/i }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /Parametric things/i })).toBeVisible();

  // Forward into a different model.
  await page.locator('a[href="/models/cylindrical-holder-slot"]').click();
  await expect(page).toHaveURL(/\/models\/cylindrical-holder-slot$/);
});
