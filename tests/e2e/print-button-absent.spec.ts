import { expect, test, type Page } from "@playwright/test";
import { waitForRenderReady } from "./support/render";

// pst-62i6h: the Print button exists only when NEXT_PUBLIC_PRINT_BRIDGE_URL
// is baked into the build AND the tailnet bridge answers /health. Neither
// the CI build nor playwright.config.ts sets the var, so the page must look
// exactly as before: Download present, no Print button, and no request to
// any off-origin /health (the probe never runs).

test.skip(
  !!process.env.NEXT_PUBLIC_PRINT_BRIDGE_URL,
  "NEXT_PUBLIC_PRINT_BRIDGE_URL is set in this runner — the absent case can't be checked",
);

function watchOffOriginHealth(page: Page, baseURL: string): string[] {
  const hits: string[] = [];
  const origin = new URL(baseURL).origin;
  page.on("request", (req) => {
    const url = new URL(req.url());
    if (url.origin !== origin && url.pathname.endsWith("/health")) hits.push(req.url());
  });
  return hits;
}

test("SCAD model page has no Print button without the env var", async ({ page, baseURL }) => {
  const probes = watchOffOriginHealth(page, baseURL!);
  await page.goto("/models/popcorn-kernel");
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");
  await waitForRenderReady(page);

  await expect(page.getByRole("button", { name: /Download STL/i })).toBeEnabled();
  await expect(page.getByTestId("print-button")).toHaveCount(0);
  expect(probes).toEqual([]);
});

test("build123d model page has no Print button without the env var", async ({ page, baseURL }) => {
  test.skip(
    process.env.BD_MODELS_ENABLED !== "1",
    "build123d pages are opt-in (BD_MODELS_ENABLED=1, presets baked)",
  );
  const probes = watchOffOriginHealth(page, baseURL!);
  await page.goto("/models/holder-spray-can");

  await expect(page.getByTestId("bd-download-stl")).toBeVisible();
  await expect(page.getByTestId("print-button")).toHaveCount(0);
  expect(probes).toEqual([]);
});
