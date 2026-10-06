import { expect, test } from "@playwright/test";

test.skip(process.env.BD_MODELS_ENABLED !== "1", "requires build123d preset bakes");

const slug = "littletikes-dream-machine-cartridge-holder";

test("cartridge slug opens the build123d holder and all four baked presets", async ({ page }) => {
  await page.goto("/");
  const card = page.locator(`a[href="/models/${slug}"]`);
  await expect(card).toHaveCount(1);
  await card.click();
  await expect(page.getByTestId("bd-detail-root")).toBeVisible();
  await expect(page.locator("#param-mount_type")).toBeVisible();
  await expect(page.locator("#param-snap_every_cell")).toHaveCount(0);
  await expect(page.getByTestId("bd-preset-sparse_snaps")).toHaveCount(0);

  for (const [preset, mount] of [
    ["default", "opengrid"],
    ["full_holder", "opengrid"],
    ["blank_back", "blank"],
    ["openconnect", "openconnect"],
  ]) {
    await page.getByTestId(`bd-preset-${preset}`).click();
    await expect(page.locator("#param-mount_type")).toHaveValue(mount);
    await expect(page.getByTestId("bd-glb-size")).toBeVisible();
    const response = await page.request.get(`/api/bd-asset/${slug}/${preset}?format=stl`);
    expect(response.status()).toBe(200);
    expect((await response.body()).length).toBeGreaterThan(84);
  }
});
