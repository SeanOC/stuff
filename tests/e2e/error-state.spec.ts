import { expect, test } from "@playwright/test";

// Exercises the Caliper error-state UI (st-bg4) end-to-end against a
// deliberately malformed .scad fixture (tests/fixtures/models/
// broken_syntax.scad, served by app/dev/broken-syntax/). Pinning
// this in E2E catches regressions the jsdom component tests miss —
// e.g. WASM path differences, Tailwind slide transition timing,
// modal focus handling.

const BROKEN = "/dev/broken-syntax";

test.describe("error state", () => {
  test("error strip shows line number and message; modal opens + closes", async ({ page }) => {
    await page.goto(BROKEN);

    // Phase 2b (st-psn): Enter from the focused viewer triggers the
    // first render, same pattern preview-controls.spec.ts uses.
    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");

    // The strip stays mounted to play its transition — check
    // aria-hidden flipping to "false" as the "error state entered"
    // signal rather than toBeVisible (which passes on the empty
    // off-screen placeholder too).
    const strip = page.getByTestId("error-strip");
    await expect(strip, "error strip enters shown state").toHaveAttribute(
      "aria-hidden",
      "false",
      { timeout: 60_000 },
    );

    // Broken fixture is an unterminated expression; OpenSCAD reports
    // the error at an end-of-file line number — we don't pin the
    // exact digit, just that some `line N` is shown and a recognizable
    // fragment of the parser message renders.
    await expect(strip).toContainText(/line \d+/);
    await expect(strip).toContainText(/Parser error|syntax error/i);

    // Full-log modal opens on click and contains the raw stderr.
    await strip.getByRole("button", { name: /view full log/i }).click();
    const modal = page.getByTestId("error-log-modal");
    await expect(modal).toBeVisible();
    await expect(modal).toContainText(/ERROR:/);

    // Escape closes the modal.
    await page.keyboard.press("Escape");
    await expect(modal).toBeHidden();

    // Re-open; backdrop click closes it too. Phase 3a (st-1j9)
    // migrated ErrorLogModal to the shared <Modal>, which puts the
    // click-to-close handler on the outer role="presentation"
    // backdrop. Click there, not on the dialog body.
    await strip.getByRole("button", { name: /view full log/i }).click();
    const reopened = page.getByTestId("error-log-modal");
    await expect(reopened).toBeVisible();
    await page.locator('[role="presentation"]').click({ position: { x: 5, y: 5 } });
    await expect(reopened).toBeHidden();
  });

  test("navigating to a valid model clears the error state", async ({ page }) => {
    // Error first.
    await page.goto(BROKEN);
    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");
    await expect(page.getByTestId("error-strip")).toBeVisible({
      timeout: 60_000,
    });

    // Cross-route navigation remounts DetailPage — the render log +
    // history reset, and the new page returns to idle until Enter.
    // (Last-good-render dim-behind across routes is out of scope;
    // the jsdom test covers the within-route dim overlay.)
    //
    // The strip stays mounted so its slide-out transition can play;
    // in non-error states it flips aria-hidden=true and translates
    // off-screen. Check the aria attribute rather than .toBeHidden()
    // so the transform-based hide counts.
    await page.goto("/models/popcorn-kernel");
    await expect(page.getByTestId("error-strip")).toHaveAttribute(
      "aria-hidden",
      "true",
    );

    await page.locator('section[aria-label="3D preview"]').focus();
    await page.keyboard.press("Enter");
    // Stat-strip dimensions appear once the hook has transitioned
    // back to `ready` on this route. (Swapped from the render-log
    // entry which st-j98 now hides behind the collapsed left rail.)
    await expect(
      page.getByTestId("stat-strip-dimensions"),
    ).toBeVisible({ timeout: 60_000 });
  });
});
