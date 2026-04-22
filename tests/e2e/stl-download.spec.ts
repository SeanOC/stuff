import { expect, test } from "@playwright/test";

// Exercises the full export path. The download → file-read round-trip
// is what catches "button click does nothing" and "blob empty" regressions
// — the preview-rerender test doesn't cover the API export route at all.

test("Download STL produces a non-empty STL file", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  // Wait for first preview render so the button isn't disabled.
  await expect(page.getByText(/rendered in \d+ms · [\d,]+ bytes/)).toBeVisible({ timeout: 60_000 });
  const button = page.getByRole("button", { name: /Download STL/i });
  await expect(button).toBeEnabled();

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    button.click(),
  ]);

  expect(download.suggestedFilename()).toBe("popcorn_kernel.stl");

  const path = await download.path();
  expect(path).toBeTruthy();
  const { readFileSync, statSync } = await import("node:fs");
  const size = statSync(path!).size;
  expect(size).toBeGreaterThan(1000);

  const head = readFileSync(path!, "utf8").slice(0, 32);
  expect(head.startsWith("solid")).toBe(true);
});
