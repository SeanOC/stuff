// Config for the param-sweep connectivity guard (tests/sweep/).
// Separate from vitest.config.ts because the sweep renders hundreds of
// wasm models (minutes, not seconds) — run with `npm run test:sweep`.
import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  test: {
    include: ["tests/sweep/**/*.test.ts"],
    environment: "node",
    testTimeout: 300_000,
    // Each worker holds a wasm heap while rendering; cap the fan-out so
    // a many-core machine doesn't balloon memory. Per-model test files
    // still parallelize up to this cap.
    maxWorkers: 4,
    minWorkers: 1,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
