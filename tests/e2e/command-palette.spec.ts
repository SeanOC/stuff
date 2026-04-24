import { expect, test, type Page } from "@playwright/test";

// Covers the Caliper command palette (st-3lc):
// - ⌘K / top-bar button open it
// - substring filter narrows the result set
// - ↑↓ move the cursor, Enter activates
// - model rows navigate
// - action rows dispatch (shortcut sheet open, go to library)
// - ? opens the shortcut sheet independently
// - Escape closes

const IS_MAC = process.platform === "darwin";
const MOD = IS_MAC ? "Meta" : "Control";

// Global shortcuts (⌘K, ⌘L, ?) live in the GlobalShortcuts client
// island. Its useShortcut effects register window keydown listeners
// during hydration — not on the `load` event Playwright's goto
// resolves on. Waiting for the Search button's onClick to be ready
// is a deterministic hydration gate: both handlers land in the same
// pass.
async function waitForHydration(page: Page) {
  await expect(
    page.getByRole("button", { name: /open command palette/i }),
  ).toBeEnabled();
}

test.describe("command palette", () => {
  test("⌘K from the library opens the palette", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    await expect(
      page.getByRole("dialog", { name: /command palette/i }),
    ).toBeVisible();
    await expect(page.getByPlaceholder(/search or run a command/i)).toBeFocused();
  });

  test("top-bar Search button opens the palette", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /open command palette/i }).click();
    await expect(
      page.getByRole("dialog", { name: /command palette/i }),
    ).toBeVisible();
  });

  test("substring filter narrows results; Enter navigates to a model", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);

    const input = page.getByPlaceholder(/search or run a command/i);
    await input.fill("popcorn");

    // Actions / Recent / Presets groups drop out when their rows
    // don't match the query — only Models should remain.
    await expect(page.getByTestId("palette-group-models")).toBeVisible();
    await expect(page.getByTestId("palette-group-actions")).toHaveCount(0);

    // The cursor is at position 0; Enter activates the first visible
    // match, which for "popcorn" is the popcorn-kernel model row.
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/models\/popcorn-kernel$/);
  });

  test("Arrow keys move the selection; the selected row carries aria-selected", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    await page.getByPlaceholder(/search or run a command/i).fill("model");

    const first = page
      .locator('[role="option"][aria-selected="true"]')
      .first();
    const initialText = await first.textContent();

    await page.keyboard.press("ArrowDown");
    const afterMove = await page
      .locator('[role="option"][aria-selected="true"]')
      .first()
      .textContent();
    expect(afterMove).not.toBe(initialText);
  });

  test("Go to library action navigates home", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    await page.getByPlaceholder(/search or run a command/i).fill("library");
    await page.getByTestId("palette-cmd-action:library").click();
    await expect(page).toHaveURL(/\/$/);
  });

  test("Open shortcut sheet action swaps modals", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    await page.getByPlaceholder(/search or run a command/i).fill("shortcut");
    await page.getByTestId("palette-cmd-action:shortcuts").click();
    await expect(
      page.getByRole("dialog", { name: /keyboard shortcuts/i }),
    ).toBeVisible();
  });

  test("? opens the shortcut sheet directly (without palette first)", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    // Shift+/ emits "?" — the useShortcut binding listens for the
    // "?" key directly.
    await page.keyboard.press("Shift+Slash");
    await expect(
      page.getByRole("dialog", { name: /keyboard shortcuts/i }),
    ).toBeVisible();
  });

  test("⌘L navigates to the library", async ({ page }) => {
    await page.goto("/models/popcorn-kernel");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyL`);
    await expect(page).toHaveURL(/\/$/);
  });

  test("Escape closes the palette", async ({ page }) => {
    await page.goto("/");
    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    await expect(
      page.getByRole("dialog", { name: /command palette/i }),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(
      page.getByRole("dialog", { name: /command palette/i }),
    ).toBeHidden();
  });

  test("Recent group populates after visiting a detail page", async ({ page }) => {
    // Clear any prior localStorage state (Playwright isolates contexts
    // but be explicit so this test is self-contained).
    await page.goto("/");
    await page.evaluate(() =>
      localStorage.removeItem("stuff.v1.recent.models"),
    );

    // Visit two models so Recent has content.
    await page.goto("/models/popcorn-kernel");
    await page.goto("/models/cylindrical-holder-slot");

    await waitForHydration(page);
    await page.keyboard.press(`${MOD}+KeyK`);
    const recent = page.getByTestId("palette-group-recent");
    await expect(recent).toBeVisible();
    // Most-recent-first, so cylindrical-holder should appear before
    // popcorn-kernel inside the Recent group.
    await expect(recent).toContainText(/cylindrical/i);
    await expect(recent).toContainText(/popcorn/i);
  });
});
