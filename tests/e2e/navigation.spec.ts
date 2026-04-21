import { expect, test } from "@playwright/test";

test("gallery ↔ model page round-trip via link + back button", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /stuff — parametric models/ })).toBeVisible();

  await page.locator('a[href="/models/smoke-motor-mount"]').click();
  await expect(page).toHaveURL(/\/models\/smoke-motor-mount$/);
  await expect(page.getByRole("link", { name: /all models/i })).toBeVisible();

  // "← all models" link back to gallery.
  await page.getByRole("link", { name: /all models/i }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /stuff — parametric models/ })).toBeVisible();

  // Forward into a different model.
  await page.locator('a[href="/models/cylindrical-holder-slot"]').click();
  await expect(page).toHaveURL(/\/models\/cylindrical-holder-slot$/);
});
