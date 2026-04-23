import { expect, test } from "@playwright/test";

// st-fl4: at ≥1200px the detail page pins to the viewport (top bar +
// viewer + rails all fit inside 100vh - 38px), and the param rail
// scrolls internally when its content is taller than the column. If
// the whole page scrolls the viewer goes above the fold and the
// user loses sight of their change's effect.

test.describe("detail page layout", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("param rail scrolls internally, document does not scroll", async ({ page }) => {
    // cylindrical_holder_slot has 12 @params — tallest current fixture.
    await page.goto("/models/cylindrical-holder-slot");
    // Phase 2b (st-psn): first render is user-triggered via Enter.
    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/\d+ms · [\d.]+kb/).first()).toBeVisible({
      timeout: 60_000,
    });

    const metrics = await page.evaluate(() => {
      const doc = document.documentElement;
      const rail = document.querySelector<HTMLElement>('[data-testid="param-rail-col"]');
      const root = document.querySelector<HTMLElement>('[data-testid="detail-root"]');
      return {
        docScroll: doc.scrollHeight - doc.clientHeight,
        rootHeight: root?.clientHeight ?? 0,
        railScrollHeight: rail?.scrollHeight ?? 0,
        railClientHeight: rail?.clientHeight ?? 0,
        winHeight: window.innerHeight,
      };
    });

    // The document itself doesn't overflow. 1px of slop tolerance for
    // sub-pixel rounding under fractional device pixel ratios.
    expect(metrics.docScroll).toBeLessThanOrEqual(1);

    // The root layout fits within viewport-minus-topbar (38px sticky).
    expect(metrics.rootHeight).toBeLessThanOrEqual(metrics.winHeight - 38 + 1);

    // The param rail column has more content than it shows: this
    // confirms internal overflow is the mechanism, not "content just
    // happens to fit". If cylindrical_holder_slot ever slims down, this
    // assertion loses meaning — pick a longer fixture then.
    expect(metrics.railScrollHeight).toBeGreaterThan(metrics.railClientHeight);

    // Scrolling inside the param rail does NOT move the document.
    await page.evaluate(() => {
      const rail = document.querySelector<HTMLElement>('[data-testid="param-rail-col"]');
      rail!.scrollTop = 200;
    });
    const after = await page.evaluate(() => ({
      doc: document.documentElement.scrollTop,
      rail: document.querySelector<HTMLElement>('[data-testid="param-rail-col"]')!.scrollTop,
    }));
    expect(after.doc).toBe(0);
    expect(after.rail).toBeGreaterThan(0);

    // Viewer canvas stays fully within the viewport (not scrolled off
    // the top, not clipped past the bottom).
    const canvasBox = await page.locator("canvas").first().boundingBox();
    expect(canvasBox, "canvas has no bounding box").not.toBeNull();
    expect(canvasBox!.y).toBeGreaterThanOrEqual(0);
    expect(canvasBox!.y + canvasBox!.height).toBeLessThanOrEqual(metrics.winHeight + 1);
  });
});

// Below 1200px the grid stacks to a single column. The viewport-pin
// is intentionally off there — the page flows naturally. Phase 4 owns
// the real mobile bottom-sheet layout; this test just guards that the
// sub-xl path doesn't regress into a broken pin.
test.describe("detail page layout — stacked (< xl)", () => {
  test.use({ viewport: { width: 1100, height: 800 } });

  test("stacked layout scrolls the document naturally", async ({ page }) => {
    await page.goto("/models/cylindrical-holder-slot");
    // Phase 2b (st-psn): first render is user-triggered via Enter.
    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");
    await expect(page.getByText(/\d+ms · [\d.]+kb/).first()).toBeVisible({
      timeout: 60_000,
    });

    const metrics = await page.evaluate(() => ({
      docScroll: document.documentElement.scrollHeight - document.documentElement.clientHeight,
    }));
    // Long stack → document scroll is expected here, not a bug.
    expect(metrics.docScroll).toBeGreaterThan(0);
  });
});
