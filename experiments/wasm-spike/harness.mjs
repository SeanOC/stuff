// st-556 Phase 0 WASM feasibility harness.
//
// Mounts the repo's vendored libs (BOSL2 + QuackWorks) into the
// openscad-wasm virtual filesystem and runs the bead's three probes
// in order. Each probe captures: ok, render time, STL size, peak RSS,
// stderr lines (warnings/errors).
//
// Run: node harness.mjs
// Output: one JSON object to stdout, exit 0 even on probe failures
// (we WANT to see how far we got).

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createOpenSCAD } from "openscad-wasm-prebuilt";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");
const LIBS_DIR = path.join(REPO_ROOT, "libs");
const MODELS_DIR = path.join(REPO_ROOT, "models");

// ---- helpers ----------------------------------------------------------

function copyTreeIntoFS(instance, hostDir, fsDir) {
  // Recursively copy a host directory tree into the Emscripten FS.
  // Returns count of .scad files written so we can sanity-check the
  // mount. Follows symlinks (libs/ entries are symlinks into the
  // shared lib clone outside the worktree).
  let count = 0;
  try { instance.FS.mkdir(fsDir); } catch { /* exists */ }
  for (const name of fs.readdirSync(hostDir)) {
    const hostPath = path.join(hostDir, name);
    const fsPath = `${fsDir}/${name}`;
    const stat = fs.statSync(hostPath); // follows symlinks
    if (stat.isDirectory()) {
      count += copyTreeIntoFS(instance, hostPath, fsPath);
    } else if (stat.isFile() && name.endsWith(".scad")) {
      const data = fs.readFileSync(hostPath);
      instance.FS.writeFile(fsPath, data);
      count++;
    }
  }
  return count;
}

async function probe({ name, scadSource, scadFromFile, backend = "Manifold" }) {
  // Each probe gets a fresh openscad instance — a CGAL/Manifold crash
  // in one probe corrupts the WASM heap and cascades into the next, so
  // we throw the instance away after each one.
  const stderr = [];
  const openscad = await createOpenSCAD({
    print: () => {},
    printErr: (line) => stderr.push(line),
  });
  const instance = openscad.getInstance();
  copyTreeIntoFS(instance, LIBS_DIR, "/libraries");

  let ok = false;
  let stlBytes = 0;
  let firstError = null;
  const t0 = process.hrtime.bigint();
  try {
    const inputPath = "/probe_input.scad";
    const outputPath = "/probe_output.stl";
    const source = scadSource ?? fs.readFileSync(scadFromFile, "utf8");
    instance.FS.writeFile(inputPath, source);
    const rc = instance.callMain([
      inputPath,
      "-o", outputPath,
      "--backend", backend,
    ]);
    if (rc === 0) {
      const stl = instance.FS.readFile(outputPath, { encoding: "binary" });
      stlBytes = stl.length;
      ok = stlBytes > 0;
    } else {
      firstError = `callMain rc=${rc}`;
    }
  } catch (e) {
    // Emscripten throws integer pointers on abort; stringify whatever.
    firstError = `wasm_abort=${String(e?.message ?? e)}`;
  }
  const elapsedMs = Number(process.hrtime.bigint() - t0) / 1e6;
  const mem = process.memoryUsage();
  return {
    name,
    backend,
    ok,
    render_ms: +elapsedMs.toFixed(1),
    stl_bytes: stlBytes,
    rss_mb: +(mem.rss / 1024 / 1024).toFixed(1),
    heap_used_mb: +(mem.heapUsed / 1024 / 1024).toFixed(1),
    error: firstError,
    stderr_lines: stderr.length,
    stderr_warnings: stderr.filter((l) => /warning/i.test(l)).slice(0, 5),
    stderr_errors: stderr.filter((l) => /(error|undefined|cannot)/i.test(l)).slice(0, 8),
    stderr_tail: stderr.slice(-12),
  };
}

// ---- main -------------------------------------------------------------

const probes = [];

probes.push(await probe({
  name: "1-trivial-cube",
  scadSource: `cube([10, 10, 10]);`,
}));

// 2a: synthetic BOSL2-only sanity check. The bead lists
// spraycan_holder_70mm.scad as "pure BOSL2", but its actual source
// also `use`s QuackWorks/snapConnector. This synthetic probe isolates
// BOSL2 cleanly so we can attribute any failure correctly.
probes.push(await probe({
  name: "2a-bosl2-synthetic",
  scadSource: `
    include <BOSL2/std.scad>
    cuboid([20, 30, 10], rounding=2, edges="Z");
  `,
}));

probes.push(await probe({
  name: "2-spraycan-holder-70mm",
  scadFromFile: path.join(MODELS_DIR, "spraycan_holder_70mm.scad"),
}));

probes.push(await probe({
  name: "3-cylindrical-holder-slot",
  scadFromFile: path.join(MODELS_DIR, "cylindrical_holder_slot.scad"),
}));

console.log(JSON.stringify({
  package: "openscad-wasm-prebuilt@1.2.0",
  package_source: "https://github.com/lorenzowritescode/openscad-wasm",
  openscad_version: "2025.01.19",
  node_version: process.version,
  default_backend: "Manifold",
  probes,
}, null, 2));
