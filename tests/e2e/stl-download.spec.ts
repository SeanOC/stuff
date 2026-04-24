import { expect, test } from "@playwright/test";

// Exercises the full export path. The download → file-read round-trip
// is what catches "button click does nothing" and "blob empty" regressions
// — the preview-rerender test doesn't cover the API export route at all.

test("Download STL produces a non-empty STL file", async ({ page }) => {
  await page.goto("/models/popcorn-kernel");

  // Phase 2b (st-psn): the viewer starts idle and the Download STL
  // button is disabled until a render completes. Press Enter to kick
  // the first render, wait for the log entry, and only then assert
  // the button is enabled.
  const button = page.getByRole("button", { name: /Download STL/i });
  await expect(button).toBeDisabled();

  await page.locator('section[aria-label="3D preview"]').focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("stat-strip-dimensions")).toBeVisible({ timeout: 60_000 });
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
