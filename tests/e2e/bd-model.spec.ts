import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page, type Route } from "@playwright/test";

// End-to-end for the build123d live-param flow (bead pst-qbas, P2c). The
// bd detail page loads its baked GLB, exposes EDITABLE params, live-renders
// tweaks via /api/bd-render on an explicit Update (never on preset select),
// and downloads an STL of the current live params.
//
// Opt-in. The whole feature is gated on BD_MODELS_ENABLED, and the preset
// GLB viewer + baked bytes need the presets baked into build123d/baked/.
// So this spec only runs when a run explicitly enables it:
//
//   bash scripts/vendor-libs.sh                     # once
//   BD_MODELS_ENABLED=1 bash scripts/bake-bd-presets.sh
//   BD_MODELS_ENABLED=1 npm run test:e2e -- bd-model
//
// The live-render specs stub /api/bd-render (page.route) with the baked
// bytes: build123d renders only in a scale-to-zero Cloud Run service that
// isn't reachable from a test run, so the stub exercises the UI flow
// deterministically while the preset view uses the real baked assets.
//
// playwright.config.ts passes BD_MODELS_ENABLED through to the web server,
// so the same var both un-skips this spec and un-hides the bd pages. Unset
// in CI → the pages stay hidden and this spec skips, leaving the required
// e2e check untouched.
test.skip(
  process.env.BD_MODELS_ENABLED !== "1",
  "build123d live-param flow is opt-in (set BD_MODELS_ENABLED=1 and bake first)",
);

const SLUG = "holder-spray-can";
const PRESET = "spray_can";
const BAKED_ROOT = path.resolve(process.cwd(), "build123d", "baked", SLUG);

const bakedGlb = () => readFileSync(path.join(BAKED_ROOT, `${PRESET}.glb`));
const bakedStl = () => readFileSync(path.join(BAKED_ROOT, `${PRESET}.stl`));

async function expectUprightBbox(page: Page): Promise<void> {
  // GLB load populates the bbox strip. data-glb-size = "x,y,z" in the
  // GLB's own units (metres, from OCP). Orientation assertion: pin the
  // known-good upright envelope for this preset (collar h=60mm → Y-up,
  // back-plate depth pushing Z past it). A double -90°X rotation would
  // swap Y and Z, dropping the 60mm height into Z (< 0.062).
  const sizeEl = page.getByTestId("bd-glb-size");
  await expect(sizeEl).toBeVisible({ timeout: 30_000 });
  const raw = await sizeEl.getAttribute("data-glb-size");
  expect(raw).toBeTruthy();
  const [x, y, z] = raw!.split(",").map(Number);
  expect(Number.isFinite(x) && Number.isFinite(y) && Number.isFinite(z)).toBe(true);
  expect(y).toBeCloseTo(0.06, 2);
  expect(z).toBeGreaterThan(0.062);
}

test("bd page loads with EDITABLE params (no presets-only banner) and renders upright", async ({
  page,
}) => {
  await page.goto(`/models/${SLUG}`);

  // The bd detail shell, not the SCAD DetailPage.
  await expect(page.getByTestId("bd-detail-root")).toBeVisible();
  // P2c removed the read-only banner + table: params are now editable.
  await expect(page.getByTestId("bd-presets-only-notice")).toHaveCount(0);
  await expect(page.getByTestId("bd-preset-spray_can")).toBeVisible();
  // ParamRail is mounted with real, editable controls (manifest param `d`).
  await expect(page.locator("#param-d")).toBeVisible();

  await expectUprightBbox(page);

  // Orientation compass parity with the SCAD viewer (pst-6ram).
  const compass = page.getByTestId("axes-indicator");
  await expect(compass).toBeVisible();
  await expect(compass.locator('g[data-axis="x"] line')).toBeVisible();
  await expect(compass.locator('g[data-axis="y"] line')).toBeVisible();
  await expect(compass.locator('g[data-axis="z"] line')).toBeVisible();
});

test("selecting a preset loads the baked GLB with NO bd-render service call", async ({
  page,
}) => {
  let renderCalls = 0;
  await page.route(/\/api\/bd-render/, async (route: Route) => {
    renderCalls++;
    await route.fulfill({ status: 503, body: JSON.stringify({ disabled: true }) });
  });

  await page.goto(`/models/${SLUG}`);
  await expect(page.getByTestId("bd-detail-root")).toBeVisible();
  await expectUprightBbox(page);

  // Re-select the preset — the instant baked path, never the service.
  await page.getByTestId(`bd-preset-${PRESET}`).click();
  await expect(page.getByTestId("bd-detail-root")).toHaveAttribute(
    "data-bd-source",
    "preset",
  );
  // Give any stray request a beat to land, then assert none did.
  await page.waitForTimeout(300);
  expect(renderCalls).toBe(0);
});

test("param tweak → Update → live render (warming state, then live source)", async ({
  page,
}) => {
  const glb = bakedGlb();
  await page.route(/\/api\/bd-render/, async (route: Route) => {
    // Slow enough to observe the warming state before the bytes land.
    await new Promise((r) => setTimeout(r, 500));
    await route.fulfill({
      status: 200,
      headers: { "content-type": "model/gltf-binary", "x-render-ms": "123" },
      body: glb,
    });
  });

  await page.goto(`/models/${SLUG}`);
  const root = page.getByTestId("bd-detail-root");
  await expect(root).toBeVisible();
  await expectUprightBbox(page);
  await expect(root).toHaveAttribute("data-bd-source", "preset");

  // Tweak a param — the view goes stale but must NOT render yet.
  await page.locator("#param-d").fill("70");
  await expect(root).toHaveAttribute("data-bd-stale", "true");
  await expect(page.getByTestId("bd-stale-notice")).toBeVisible();
  await expect(root).toHaveAttribute("data-bd-source", "preset");

  // Explicit Update fires the live render.
  await page.getByTestId("bd-update-render").click();
  await expect(page.getByTestId("bd-render-warming")).toBeVisible();
  await expect(root).toHaveAttribute("data-bd-render-state", "ready", {
    timeout: 10_000,
  });
  await expect(root).toHaveAttribute("data-bd-source", "live");
});

test("STL download uses the CURRENT live params via /api/bd-render?format=stl", async ({
  page,
}) => {
  const stl = bakedStl();
  let sawStlRequest = false;
  let sentParamD: unknown = null;
  await page.route(/\/api\/bd-render\?format=stl/, async (route: Route) => {
    sawStlRequest = true;
    try {
      const body = route.request().postDataJSON() as { params?: Record<string, unknown> };
      sentParamD = body?.params?.d;
    } catch {
      /* leave null */
    }
    await route.fulfill({
      status: 200,
      headers: {
        "content-type": "application/sla",
        "content-disposition": `attachment; filename="${SLUG}.stl"`,
      },
      body: stl,
    });
  });

  await page.goto(`/models/${SLUG}`);
  await expect(page.getByTestId("bd-detail-root")).toBeVisible();

  // Tweak so the download must carry the CURRENT value, not the preset.
  await page.locator("#param-d").fill("70");

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByTestId("bd-download-stl").click(),
  ]);
  expect(sawStlRequest).toBe(true);
  expect(Number(sentParamD)).toBe(70);
  expect(download.suggestedFilename()).toBe(`${SLUG}.stl`);
  const p = await download.path();
  expect(p).toBeTruthy();
  const { statSync } = await import("node:fs");
  expect(statSync(p!).size).toBeGreaterThan(1000);
});

test("a disabled/unreachable service shows a friendly error (no WASM fallback)", async ({
  page,
}) => {
  await page.route(/\/api\/bd-render/, async (route: Route) => {
    await route.fulfill({
      status: 503,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ error: "build123d live render is disabled", disabled: true }),
    });
  });

  await page.goto(`/models/${SLUG}`);
  const root = page.getByTestId("bd-detail-root");
  await expect(root).toBeVisible();

  await page.locator("#param-d").fill("70");
  await page.getByTestId("bd-update-render").click();

  await expect(page.getByTestId("bd-render-error")).toBeVisible();
  await expect(root).toHaveAttribute("data-bd-render-state", "error");
  // Still the last-good (preset) geometry — no fallback renderer kicked in.
  await expect(root).toHaveAttribute("data-bd-source", "preset");
});

test("gallery thumbnail is served from the baked preset (single source)", async ({
  request,
}) => {
  // /api/thumbnail serves build123d cards from the same bake that produced
  // the GLB (build123d/baked/<slug>/<preset>.png), so the listing card can
  // never drift from the shipped geometry (bead pst-1vi5).
  const res = await request.get(`/api/thumbnail?model=${encodeURIComponent(SLUG)}`);
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toBe("image/png");
  const body = await res.body();
  expect(body.byteLength).toBeGreaterThan(1000);
});
