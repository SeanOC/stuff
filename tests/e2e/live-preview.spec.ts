import { expect, test, type Page } from "@playwright/test";

// Scope guard for the Phase 1/2 silent-override bug: when the form
// reports new values but the render doesn't actually see them, the
// status-line byte count stays identical and tests still pass visually.
// This spec asserts the byte count *changes* across param edits — if
// overrides stop applying, this test fails with a clear diff.

async function readStatusBytes(page: Page): Promise<number> {
  const line = page.getByText(/rendered in \d+ms · [\d,]+ bytes/);
  await expect(line).toBeVisible({ timeout: 60_000 });
  const txt = (await line.textContent()) ?? "";
  const m = txt.match(/·\s*([\d,]+) bytes/);
  if (!m) throw new Error(`status line missing bytes: ${txt}`);
  return Number(m[1].replace(/,/g, ""));
}

test("changing a param re-renders with a different STL", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  const initial = await readStatusBytes(page);

  // Bump plate width up significantly; bigger plate → more triangles
  // → larger STL byte count. Wait past the 250ms render debounce.
  const input = page.locator("#param-plate_w");
  await input.fill("160");
  await page.waitForTimeout(400);

  // Status line cycles through "rendering…" → "rendered in …". Wait
  // for the final rendered state, then re-read bytes.
  await expect(page.getByText(/rendering…/)).toBeVisible({ timeout: 2_000 }).catch(() => {
    // Fast renders may skip the visible rendering state — not a failure.
  });
  await expect(page.getByText(/rendered in \d+ms · [\d,]+ bytes/)).toBeVisible({ timeout: 60_000 });

  // Poll a few times because the byte count updates asynchronously
  // after the re-render completes.
  let updated = initial;
  for (let i = 0; i < 30; i++) {
    updated = await readStatusBytes(page);
    if (updated !== initial) break;
    await page.waitForTimeout(250);
  }
  expect(updated, "STL byte count did not change after param edit").not.toBe(initial);
});
