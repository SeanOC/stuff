import { expect, test } from "@playwright/test";

// Form validation relies on native HTML5 min/max attributes derived
// from the @param annotation. Assert the browser marks out-of-range
// numeric inputs :invalid — the same mechanism that drives
// form.reportValidity() on submit. No custom error UI today, just the
// native tooltip; if a richer error layer gets added this test is the
// place to extend it.

test("out-of-range numeric input is marked :invalid", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  // plate_w is @param number min=20 max=200.
  const plate = page.locator("#param-plate_w");
  await expect(plate).toHaveAttribute("min", "20");
  await expect(plate).toHaveAttribute("max", "200");

  await plate.fill("5");
  expect(await plate.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(false);
  expect(await plate.evaluate((el: HTMLInputElement) => el.validity.rangeUnderflow)).toBe(true);

  await plate.fill("500");
  expect(await plate.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(false);
  expect(await plate.evaluate((el: HTMLInputElement) => el.validity.rangeOverflow)).toBe(true);

  await plate.fill("80");
  expect(await plate.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(true);
});
