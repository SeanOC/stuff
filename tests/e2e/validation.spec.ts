import { expect, test } from "@playwright/test";

// Form validation relies on native HTML5 min/max attributes derived
// from the @param annotation. Assert the browser marks out-of-range
// numeric inputs :invalid — the same mechanism that drives
// form.reportValidity() on submit. No custom error UI today, just the
// native tooltip; if a richer error layer gets added this test is the
// place to extend it.

test("out-of-range numeric input is marked :invalid", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  // base_cut is @param number min=2 max=10 — the cheapest annotated
  // model (no BOSL2 includes) so the test doesn't pay the cold-WASM tax.
  const cut = page.locator("#param-base_cut");
  await expect(cut).toHaveAttribute("min", "2");
  await expect(cut).toHaveAttribute("max", "10");

  await cut.fill("1");
  expect(await cut.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(false);
  expect(await cut.evaluate((el: HTMLInputElement) => el.validity.rangeUnderflow)).toBe(true);

  await cut.fill("50");
  expect(await cut.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(false);
  expect(await cut.evaluate((el: HTMLInputElement) => el.validity.rangeOverflow)).toBe(true);

  await cut.fill("5");
  expect(await cut.evaluate((el: HTMLInputElement) => el.validity.valid)).toBe(true);
});
