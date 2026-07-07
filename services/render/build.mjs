// Bundle the render service (server.ts + render.ts + the reused
// lib/scad-params/parse.ts) into a single dependency-free ESM file the
// container runs with plain `node dist/server.mjs`. Bundling the actual
// parse.ts source is what guarantees param->define parity with the
// app/WASM path — there is no second copy to drift.
//
// Run from the repo root or this dir: `node services/render/build.mjs`.

import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));

await build({
  entryPoints: [path.join(here, "server.ts")],
  outfile: path.join(here, "dist", "server.mjs"),
  bundle: true,
  platform: "node",
  format: "esm",
  target: "node20",
  // Only node stdlib remains external; everything first-party is inlined.
  packages: "external",
  logLevel: "info",
});
