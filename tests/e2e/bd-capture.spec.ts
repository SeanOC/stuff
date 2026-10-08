import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import manifest from "../../build123d/manifest.json";
import { downloadFilename } from "../../lib/models/download-name";
import type { Param, ParamValue } from "../../lib/scad-params/parse";

test.skip(process.env.BD_MODELS_ENABLED !== "1", "Capture requires BD_MODELS_ENABLED=1 and baked presets");

const SLUG = "gridfinity-capture-bin";
const model = manifest.models.find(m => m.slug === SLUG)!;
const baked = (ext: string, preset = "default") => readFileSync(path.resolve("build123d/baked", SLUG, `${preset}.${ext}`));

test("photo stays local, detector is lazy, overlay applies once and live STL uses current values", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const detectorRequests: string[] = [];
  const firstLoadChunks: string[] = [];
  const renderBodies: Array<{ slug: string; params: Record<string, ParamValue> }> = [];
  let downloadValues: Record<string, ParamValue> | undefined;
  page.on("request", request => {
    if (request.url().includes("/vendor/opencv/")) detectorRequests.push(request.url());
  });
  page.on("response", response => {
    if (response.url().includes("/_next/static/") && response.url().endsWith(".js"))
      firstLoadChunks.push(response.url());
  });
  // A different envelope proves the live GLB parsed and called onLoaded;
  // the old preset's bbox strip alone would also satisfy toBeVisible().
  const glb = baked("glb", "deep");
  await page.route("**/api/bd-render**", async route => {
    expect(route.request().method()).toBe("POST");
    const body = route.request().postDataJSON();
    if (new URL(route.request().url()).searchParams.get("format") === "stl") {
      downloadValues = body.params;
      await route.fulfill({ contentType: "application/sla", body: baked("stl", "deep") });
    } else {
      renderBodies.push(body);
      await route.fulfill({ contentType: "model/gltf-binary", body: glb });
    }
  });

  await page.goto(`/models/${SLUG}`);
  await expect(page.getByRole("heading", { name: "Capture an item outline" })).toBeVisible();
  await expect(page.getByTestId("bd-glb-size")).toBeVisible();
  const originalSize = await page.getByTestId("bd-glb-size").getAttribute("data-glb-size");
  expect(originalSize).toBeTruthy();
  expect(detectorRequests).toEqual([]);
  expect(renderBodies).toEqual([]);
  // Preserve the actual first-load resource list for production bundle evidence.
  await testInfo.attach("first-load-chunks", { body: firstLoadChunks.join("\n"), contentType: "text/plain" });
  const firstLoadSources = await Promise.all(firstLoadChunks.map(async url => (await page.request.get(url)).text()));
  for (const source of firstLoadSources) {
    expect(source).not.toContain("vendor/opencv");
    expect(source).not.toContain("onRuntimeInitialized");
  }

  await Promise.all([
    page.waitForRequest("**/vendor/opencv/opencv.js"),
    page.getByLabel("Take or choose a photo").setInputFiles("build123d/tests/fixtures/capture/cylinder40-p1-bare-t0.png"),
  ]);
  const overlay = page.getByLabel("Photo with detected lattice and item outline");
  await expect(overlay).toBeVisible({ timeout: 60_000 });
  expect(detectorRequests).toHaveLength(1);
  expect(renderBodies).toHaveLength(0);
  // Verify both overlay strokes are actually on the canvas, beyond visibility.
  expect(await overlay.evaluate(element => {
    const canvas = element as HTMLCanvasElement;
    const data = canvas.getContext("2d")!.getImageData(0, 0, canvas.width, canvas.height).data;
    let blue = 0, amber = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] === 56 && data[i + 1] === 189 && data[i + 2] === 248) blue++;
      if (data[i] === 251 && data[i + 1] === 191 && data[i + 2] === 36) amber++;
    }
    return blue > 100 && amber > 100;
  })).toBe(true);

  const panel = page.getByRole("region", { name: "Capture an item outline" });
  await panel.evaluate(element => window.scrollTo({ top: window.scrollY + element.getBoundingClientRect().top - 48 }));
  const screenshot = testInfo.outputPath("capture-panel-mobile.png");
  await page.screenshot({ path: screenshot });
  await testInfo.attach("capture-panel-mobile", { path: screenshot, contentType: "image/png" });

  await page.getByRole("slider", { name: /Pocket clearance/ }).fill("2.1");
  await page.locator("#param-pocket_depth").fill("45");
  await page.locator("#param-width_units").fill("5");
  await page.getByRole("button", { name: "Apply footprint" }).click();
  const root = page.getByTestId("bd-detail-root");
  await expect(root).toHaveAttribute("data-bd-source", "live");
  await expect(root).toHaveAttribute("data-bd-render-state", "ready");
  await expect(page.getByTestId("bd-glb-size")).toBeVisible();
  await expect(page.getByTestId("bd-glb-size")).not.toHaveAttribute("data-glb-size", originalSize!);
  await expect(root).toHaveAttribute("data-bd-stale", "false");
  expect(renderBodies).toHaveLength(1);
  expect(renderBodies[0].slug).toBe(SLUG);
  expect(renderBodies[0].params.clearance).toBe(2.1);
  expect(renderBodies[0].params.pocket_depth).toBe(45);
  expect(renderBodies[0].params.footprint).toBe(await page.locator("#param-footprint").inputValue());
  expect(String(renderBodies[0].params.footprint)).toMatch(/^v1;/);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("bd-download-stl").click(),
  ]);
  expect(downloadValues).toEqual(renderBodies[0].params);
  expect(download.suggestedFilename()).toBe(downloadFilename(SLUG, model.params as Param[], downloadValues!));
  expect(renderBodies).toHaveLength(1);
  expect(detectorRequests).toHaveLength(1);
});

for (const [file, error, advice] of [
  ["sharpie-daylight.png", "item crosses the plate edge", "Move the item fully inside the baseplate."],
  ["sharpie-calipers.png", "board obstructed by an object crossing its edge", "Remove anything crossing the plate edge."],
]) {
  test(`real ${file} gives actionable advice without applying a clipped footprint`, async ({ page }) => {
    const posts: string[] = [];
    page.on("request", request => { if (request.method() === "POST") posts.push(request.url()); });
    await page.goto(`/models/${SLUG}`);
    // The loaded viewer confirms hydration/effects before dispatching a file event.
    await expect(page.getByTestId("bd-glb-size")).toBeVisible();
    await page.getByLabel("Take or choose a photo").setInputFiles(`build123d/tests/fixtures/capture/real/${file}`);
    const alert = page.getByRole("region", { name: "Capture an item outline" }).getByRole("alert");
    await expect(alert).toContainText(error, { timeout: 60_000 });
    await expect(alert).toContainText(advice);
    await expect(page.getByRole("button", { name: "Apply footprint" })).toBeDisabled();
    expect(posts).toEqual([]);
  });
}
