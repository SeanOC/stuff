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
