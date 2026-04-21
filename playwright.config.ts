import { defineConfig, devices } from "@playwright/test";

// E2E config. Runs against `npm run dev` locally, `npm start` in CI
// (after `next build`). Either way we let Playwright boot the server
// itself so one command suffices.

const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 3111);
const BASE_URL = `http://127.0.0.1:${PORT}`;
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  workers: isCI ? 2 : undefined,
  reporter: isCI ? [["github"], ["html", { open: "never" }]] : "list",
  // Per-test timeout bumped above the default 30s because cold WASM
  // renders (first lib mount + Manifold build) can push past 30s on
  // a CI runner.
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    // Use the prod server in CI for fidelity; dev server locally for
    // speed. Both bind to 127.0.0.1 explicitly so `reuseExistingServer`
    // doesn't collide with a human's `next dev` on :3000.
    command: isCI
      ? `npx next start -p ${PORT} -H 127.0.0.1`
      : `npx next dev -p ${PORT} -H 127.0.0.1`,
    port: PORT,
    reuseExistingServer: !isCI,
    timeout: 120_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
