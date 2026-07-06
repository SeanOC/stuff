import { expect, test } from "@playwright/test";

// st-f43: ego_lb6500_blower_mount is the repo's first import()-based
// model. Its live preview only works if the whole binary-asset chain
// holds: closure.ts extracts the import() target from the entry
// source, /api/source serves the .stl as bytes, useRenderer fetches
// it as an ArrayBuffer, and render.ts mounts it into the WASM FS
// before calling openscad. None of that chain is exercised by the
// other e2e specs (all other models are pure CSG), so this spec pins
// it: a successful in-browser render with plausible dimensions.

test("import()-based model live-renders in the browser", async ({ page }) => {
  await page.goto("/models/ego-lb6500-blower-mount");
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");

  // A failed asset fetch surfaces as the error panel instead of the
  // stat strip; 120s budget because this render unions a 13.6k-tri
  // mesh through Manifold on WASM.
  const dims = page.getByTestId("stat-strip-dimensions");
  await expect(dims).toBeVisible({ timeout: 120_000 });
  const txt = (await dims.textContent()) ?? "";
  // 138.5 × 93.5 × 166.5 mm at defaults (PRINT_ANCHOR_BBOX).
  expect(txt).toMatch(/138\.5\s*×\s*93\.5\s*×\s*166\.5\s*mm/);
});
