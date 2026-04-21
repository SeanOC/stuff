// Probe 1: render a trivial cube via openscad-wasm-prebuilt.
// Goal: confirm the WASM loads, FS works, and we get a non-empty STL out.

import { createOpenSCAD } from "openscad-wasm-prebuilt";

const stderr = [];
const stdout = [];

const t0 = process.hrtime.bigint();
const openscad = await createOpenSCAD({
  print: (s) => stdout.push(s),
  printErr: (s) => stderr.push(s),
});
const t_init = Number(process.hrtime.bigint() - t0) / 1e6;

const t1 = process.hrtime.bigint();
const stl = await openscad.renderToStl(`cube([10, 10, 10]);`);
const t_render = Number(process.hrtime.bigint() - t1) / 1e6;

const mem = process.memoryUsage();
const out = {
  probe: "1-cube",
  ok: stl.length > 0,
  init_ms: +t_init.toFixed(1),
  render_ms: +t_render.toFixed(1),
  stl_bytes: stl.length,
  stl_starts_with: stl.slice(0, 80),
  mem_rss_mb: +(mem.rss / 1024 / 1024).toFixed(1),
  mem_heap_used_mb: +(mem.heapUsed / 1024 / 1024).toFixed(1),
  stdout_lines: stdout.length,
  stderr_lines: stderr.length,
  stderr_sample: stderr.slice(0, 5),
};
console.log(JSON.stringify(out, null, 2));
