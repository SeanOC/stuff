// Probe a candidate openscad-wasm build outside the app (pst-q0l).
//
// Drives a candidate openscad-wasm build directly (no app wiring) against
// the cases that abort on our current engine. Usage:
//   node scripts/probe-wasm-engine.mjs <engine.js> <model.scad> [-D name=value ...]
// Exits 0 only if openscad rendered a non-empty STL with no ERROR line.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { pathToFileURL } from "node:url";

const [enginePath, modelPath, ...defines] = process.argv.slice(2);
const REPO = process.env.REPO_ROOT ?? process.cwd();
const LIBS = join(REPO, "libs");

function walk(dir, out = []) {
  for (const e of readdirSync(dir)) {
    if (e === ".git") continue;
    const p = join(dir, e);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (/\.(scad|json)$/i.test(e)) out.push(p);
  }
  return out;
}

const stderr = [];
const stdout = [];
const ns = await import(pathToFileURL(enginePath).href);
const io = {
  print: (l) => stdout.push(l),
  printErr: (l) => { stderr.push(l); if (process.env.PROBE_VERBOSE) console.error("[scad]", l); },
};
let mod;
if (typeof ns.createOpenSCAD === "function") {
  // openscad-wasm-prebuilt (our current engine): wrapper API, wasm inlined.
  mod = (await ns.createOpenSCAD(io)).getInstance();
} else {
  // Raw Emscripten factory (openscad-playground). It targets the browser and
  // fetch()es its .wasm, which Node cannot do for file:// URLs; handing over
  // the bytes up front skips the fetch path entirely.
  mod = await ns.default({
    noInitialRun: true,
    wasmBinary: readFileSync(enginePath.replace(/\.js$/, ".wasm")),
    ...io,
  });
}

function mkdirp(fs, path) {
  const parts = path.split("/").filter(Boolean);
  let cur = "";
  for (const p of parts) {
    cur += "/" + p;
    try { fs.mkdir(cur); } catch {}
  }
}

// Mount the vendored library tree at /libraries (openscad-wasm convention).
let mounted = 0;
for (const lib of ["BOSL2", "QuackWorks", "gridfinity-rebuilt-openscad", "mitufy-openconnect"]) {
  const root = join(LIBS, lib);
  try { statSync(root); } catch { continue; }
  for (const f of walk(root)) {
    const rel = relative(LIBS, f);
    const dest = "/libraries/" + rel;
    mkdirp(mod.FS, dirname(dest));
    mod.FS.writeFile(dest, readFileSync(f));
    mounted++;
  }
}

mod.FS.writeFile("/input.scad", readFileSync(modelPath));

const args = ["/input.scad", "-o", "/out.stl", "--backend", "Manifold"];
for (const d of defines) args.push("-D", d.replace(/^-D/, ""));

let rc = 0, aborted = null;
const t0 = Date.now();
try {
  rc = mod.callMain(args);
} catch (e) {
  aborted = e && e.message ? e.message : String(e);
}
const ms = Date.now() - t0;

let bytes = 0, facets = 0, stlKind = "none";
try {
  const stl = mod.FS.readFile("/out.stl");
  bytes = stl.length;
  // OpenSCAD writes ASCII STL here, so sniff rather than assume binary:
  // reading the binary facet-count header off an ASCII file yields garbage.
  const head = Buffer.from(stl.slice(0, 6)).toString("latin1");
  if (head.startsWith("solid")) {
    stlKind = "ascii";
    facets = (Buffer.from(stl).toString("latin1").match(/facet normal/g) ?? []).length;
  } else if (bytes >= 84) {
    stlKind = "binary";
    facets = new DataView(stl.buffer, stl.byteOffset).getUint32(80, true);
  }
} catch {}

const errLine = stderr.find((l) => /^\s*ERROR\b/i.test(l)) ?? null;
const ok = !aborted && !errLine && facets > 0;

console.log(JSON.stringify({
  model: relative(REPO, modelPath), defines, mounted,
  rc, aborted, errLine, facets, bytes, stlKind, ms, ok,
  stderrTail: stderr.slice(-6),
}, null, 1));
process.exit(ok ? 0 : 1);
