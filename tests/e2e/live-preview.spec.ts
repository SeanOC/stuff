import { expect, test, type Page } from "@playwright/test";

// Scope guard for the Phase 1/2 silent-override bug: when the form
// reports new values but the render doesn't actually see them, the
// render log's kb count stays identical and tests still pass visually.
// This spec asserts the kb count *changes* across param edits — if
// overrides stop applying, this test fails with a clear diff.

async function readTopLogKb(page: Page): Promise<number> {
  const line = page.getByText(/\d+ms · [\d.]+kb/).first();
  await expect(line).toBeVisible({ timeout: 60_000 });
  const txt = (await line.textContent()) ?? "";
  const m = txt.match(/·\s*([\d.]+)kb/);
  if (!m) throw new Error(`render log line missing kb: ${txt}`);
  return Number(m[1]);
}

test("changing a param re-renders with a different STL", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");
  // st-j98: left rail starts collapsed, which hides the render log
  // that this test reads kb from. Expand before reading.
  await page.getByRole("button", { name: /Expand left rail/i }).click();

  // Phase 2b: kick off the first render via the idle-state Enter
  // affordance (st-psn).
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");

  const initial = await readTopLogKb(page);

  // Bump base_cut down so the chop removes less of the kernel, growing
  // the resulting STL noticeably. Wait past the 250ms render debounce.
  const input = page.locator("#param-base_cut");
  await input.fill("2");
  await page.waitForTimeout(400);

  // Log cycles through "rendering…" → a new top entry. Wait for the
  // entry to re-appear, then re-read.
  await expect(page.getByText(/\d+ms · [\d.]+kb/).first()).toBeVisible({ timeout: 60_000 });

  // Poll a few times because the render log updates asynchronously
  // after the re-render completes.
  let updated = initial;
  for (let i = 0; i < 30; i++) {
    updated = await readTopLogKb(page);
    if (updated !== initial) break;
    await page.waitForTimeout(250);
  }
  expect(updated, "STL size did not change after param edit").not.toBe(initial);
});

// Phase 2b (st-psn): the stat strip leads with per-axis dimensions
// once a render completes. Asserting the format here pins the
// "bbox went missing" regression class in the same file that pins
// the "override silently ignored" class.
test("stat strip shows W × D × H mm dimensions after render", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");
  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");

  const dims = page.getByTestId("stat-strip-dimensions");
  await expect(dims).toBeVisible({ timeout: 60_000 });
  const txt = (await dims.textContent()) ?? "";
  expect(txt).toMatch(/\d+(\.\d+)?\s*×\s*\d+(\.\d+)?\s*×\s*\d+(\.\d+)?\s*mm/);
});
