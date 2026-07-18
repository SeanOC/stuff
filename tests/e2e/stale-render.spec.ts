import { expect, test, type Page } from "@playwright/test";
import { waitForRenderReady, waitForStale } from "./support/render";

// Stale-render callout flow (pst-vfp). The viewer never blocks param
// editing; instead it flags the on-screen render as out of date once
// the live controls drift from it, and offers Revert / Re-render.
//
// All four specs key on the deterministic data-render-state /
// data-render-stale signals on the ViewerChrome section rather than
// racing async log/stat updates.

const SECTION = 'section[aria-label="3D preview"]';

async function firstRender(page: Page): Promise<void> {
  await page.goto("/models/popcorn-kernel");
  await page.locator(SECTION).focus();
  await page.keyboard.press("Enter");
  await waitForRenderReady(page);
}

test("tweaking a param mid-idle flags stale without rendering", async ({ page }) => {
  await firstRender(page);
  const section = page.locator(SECTION);

  // Baseline: fresh render, no callout.
  await expect(section).toHaveAttribute("data-render-stale", "false");
  await expect(page.getByTestId("stale-strip")).toBeHidden();
  const dimsBefore = await page.getByTestId("stat-strip-dimensions").textContent();

  // Edit a param — the preview goes stale but must NOT re-render.
  await page.locator("#param-base_cut").fill("2");
  await waitForStale(page, true);
  await expect(page.getByTestId("stale-strip")).toBeVisible();
  // Still showing the original render: state stayed ready, dims unchanged.
  await expect(section).toHaveAttribute("data-render-state", "ready");
  expect(await page.getByTestId("stat-strip-dimensions").textContent()).toBe(
    dimsBefore,
  );
});

test("Revert restores the controls and clears the callout without rendering", async ({ page }) => {
  await firstRender(page);
  const section = page.locator(SECTION);
  const input = page.locator("#param-base_cut");
  const original = await input.inputValue();

  await input.fill("2");
  await waitForStale(page, true);

  await page.getByTestId("stale-revert").click();

  // Controls snap back, callout clears, and no render was kicked off
  // (state never left "ready").
  await waitForStale(page, false);
  await expect(page.getByTestId("stale-strip")).toBeHidden();
  await expect(input).toHaveValue(original);
  await expect(section).toHaveAttribute("data-render-state", "ready");
});

test("Re-render applies the edit and clears the callout on completion", async ({ page }) => {
  await firstRender(page);
  const section = page.locator(SECTION);

  await page.locator("#param-base_cut").fill("2");
  await waitForStale(page, true);

  await page.getByTestId("stale-rerender").click();

  // The render fires and, once it lands, the displayed render matches
  // the current params again — callout gone.
  await waitForRenderReady(page);
  await waitForStale(page, false);
  await expect(page.getByTestId("stale-strip")).toBeHidden();
  await expect(section).toHaveAttribute("data-render-state", "ready");
});

test("params stay editable while a render is in flight", async ({ page }) => {
  await firstRender(page);
  const input = page.locator("#param-base_cut");

  await input.fill("2");
  await page.getByTestId("stale-rerender").click();

  // Mid-flight the control is never disabled: edit it again immediately.
  // (Playwright's fill() actionability check fails if the input is
  // disabled/readonly — so a successful fill here is the assertion.)
  await expect(input).toBeEnabled();
  await input.fill("6");
  await expect(input).toHaveValue("6");

  // And the app still converges to a good render afterwards.
  await page.getByTestId("stale-rerender").click();
  await waitForRenderReady(page);
});
