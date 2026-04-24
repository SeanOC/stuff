import { expect, test } from "@playwright/test";

// Phase 3c (st-zl5). Exercises the share flow end-to-end: URL
// round-trip (tweak → share URL → visit → param hydrates), dialog
// open + copy + toast, JSON download, and the ⌘⇧C direct-copy
// shortcut.

test.describe("share dialog", () => {
  test("URL short-keys hydrate params server-side", async ({ page }) => {
    // 46mm historic preset values for cylindrical_holder_slot —
    // can_diameter=46 is shortKey `d`, clearance=0.25 is `c`.
    await page.goto("/models/cylindrical-holder-slot?d=46&c=0.25");
    await expect(page.locator("#param-can_diameter")).toHaveValue("46");
    await expect(page.locator("#param-clearance")).toHaveValue("0.25");
  });

  test("unknown share-URL key surfaces a warning but still hydrates known keys", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot?d=48&xyz=1");
    await expect(page.locator("#param-can_diameter")).toHaveValue("48");
    // The server-decoded warning rides the left-rail warnings list.
    await expect(page.getByText(/Unknown share-URL parameter "xyz"/i)).toBeVisible();
  });

  test("opens via header Share button, Copy link fires toast and closes", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto("/models/cylindrical-holder-slot");

    // Edit a param so the URL isn't empty — the round-trip assertion
    // below wants at least one tweaked key to confirm.
    await page.locator("#param-can_diameter").fill("77");

    await page.getByRole("button", { name: /share these parameters/i }).click();
    const dialog = page.getByTestId("share-dialog");
    await expect(dialog).toBeVisible();

    const url = await page.getByTestId("share-url").textContent();
    expect(url).toMatch(/[?&]d=77/);

    await dialog.getByRole("button", { name: /copy link/i }).click();

    // Dialog closes and toast appears.
    await expect(dialog).toBeHidden();
    await expect(page.getByTestId("toast")).toBeVisible();

    // And the clipboard actually holds our URL.
    const clipped = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipped).toMatch(/[?&]d=77/);
  });

  test("Download .json writes a valid blob", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot");

    await page.getByRole("button", { name: /share these parameters/i }).click();
    const dialog = page.getByTestId("share-dialog");

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      dialog.getByRole("button", { name: /download \.json/i }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("cylindrical-holder-slot-params.json");

    const path = await download.path();
    expect(path).toBeTruthy();
    const { readFileSync } = await import("node:fs");
    const parsed = JSON.parse(readFileSync(path!, "utf8"));
    expect(parsed.modelSlug).toBe("cylindrical-holder-slot");
    expect(typeof parsed.params).toBe("object");
    expect(parsed.params.can_diameter).toBe(70); // default on this model
  });

  test("⌘⇧C direct-copies without opening the dialog", async ({
    page,
    context,
  }) => {
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.goto("/models/cylindrical-holder-slot");
    await page.locator("#param-can_diameter").fill("55");

    // Direct shortcut — no dialog should appear.
    await page.keyboard.press("Meta+Shift+C");

    await expect(page.getByTestId("toast")).toBeVisible();
    await expect(page.getByTestId("share-dialog")).toHaveCount(0);

    const clipped = await page.evaluate(() => navigator.clipboard.readText());
    expect(clipped).toMatch(/[?&]d=55/);
  });
});
