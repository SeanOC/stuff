import { expect, type Page } from "@playwright/test";

// Shared render-ready wait for the e2e suite. (pst-r5k)
//
// Every detail-page spec has to wait out the same thing before it can
// assert anything: a COLD in-browser WASM render (first lib mount +
// Manifold build) on page load. The old shape —
//
//   await expect(page.getByTestId("stat-strip-dimensions"))
//     .toBeVisible({ timeout: 60_000 });
//
// raced the appearance of a ready-ONLY child element against a fixed
// 60s budget, and timed out ("element(s) not found") whenever the cold
// render ran long. It ran long often enough to redden `main`: CI runs
// two Playwright workers in parallel, so two cold WASM renders compete
// for CPU and each takes roughly twice as long as the single-render
// figure the 60s was tuned against.
//
// This waits on the ViewerChrome state machine's own signal instead:
// the always-present `section[aria-label="3D preview"]` carries a
// `data-render-state` attribute mirroring state.kind, so we can key on
// the loading→ready transition directly. That's deterministic — the
// attribute is the render lifecycle, not a proxy for it — and it lets
// every spec share one budget instead of scattering magic 60_000s.
//
// The budget is generous on purpose: sized for the two-worker
// cold-render worst case, and kept under the per-test `timeout` in
// playwright.config.ts (which was widened to leave headroom above it).
export const RENDER_READY_TIMEOUT_MS = 90_000;

// The two terminal render states a cold render lands on. `ready` is the
// happy path; `error` is the broken-fixture path (error-state.spec.ts).
type TerminalRenderState = "ready" | "error";

// Wait until the detail page's viewer reaches a terminal render state.
// Keys on the ViewerChrome section's `data-render-state` signal, so it
// resolves on the loading→ready (or loading→error) transition itself
// rather than racing a state-specific child element. Throws on timeout.
export async function waitForRenderState(
  page: Page,
  state: TerminalRenderState,
): Promise<void> {
  await expect(
    page.locator('section[aria-label="3D preview"]'),
  ).toHaveAttribute("data-render-state", state, {
    timeout: RENDER_READY_TIMEOUT_MS,
  });
}

// Wait until the cold (or any) render completes successfully.
export function waitForRenderReady(page: Page): Promise<void> {
  return waitForRenderState(page, "ready");
}
