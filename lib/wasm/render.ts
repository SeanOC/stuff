// Browser-side WASM render driver.
//
// Lazy-loads openscad-wasm-prebuilt on first call, caches the module
// for the page lifetime, and runs each render against a freshly mounted
// include closure. Per st-556 Phase 0:
//   - openscad-wasm-prebuilt@1.2.0 (OpenSCAD 2025.01.19)
//   - --backend Manifold is mandatory; CGAL OOMs on BOSL2.
//   - Library mount path is /libraries/.
//
// renderToStl returns the binary STL plus diagnostic counts so the UI
// can show "rendered N facets in Tms".

import { buildIncludeClosure, type FileFetcher } from "./closure";

export interface RenderInput {
  /** SCAD source for the entry model. */
  source: string;
  /** Resolves a lib-relative path like "BOSL2/std.scad" to source. */
  fetchLibFile: FileFetcher;
  /** Optional `-D name=value` flags to pass to openscad. */
  defines?: string[];
}

export interface RenderResult {
  ok: boolean;
  stl?: Uint8Array;
  errorMessage?: string;
  /** Wall-clock ms for the whole render, mount included. */
  wallMs: number;
  /** Lib files mounted into FS for this render. */
  filesMounted: number;
  /** Lib paths the closure walker couldn't find. */
  missing: string[];
  /** Captured stderr lines (warnings, errors, render summary). */
  stderr: string[];
}

let cachedModule: Promise<{ createOpenSCAD: typeof import("openscad-wasm-prebuilt").createOpenSCAD }> | null = null;

function loadModule() {
  if (!cachedModule) {
    cachedModule = import("openscad-wasm-prebuilt");
  }
  return cachedModule;
}

export async function renderToStl(input: RenderInput): Promise<RenderResult> {
  const t0 = performance.now();
  const stderr: string[] = [];

  let closure;
  try {
    closure = await buildIncludeClosure({
      entrySource: input.source,
      fetchLibFile: input.fetchLibFile,
    });
  } catch (e) {
    return {
      ok: false,
      errorMessage: `closure walk failed: ${e instanceof Error ? e.message : String(e)}`,
      wallMs: performance.now() - t0,
      filesMounted: 0,
      missing: [],
      stderr,
    };
  }

  const { createOpenSCAD } = await loadModule();
  const openscad = await createOpenSCAD({
    print: () => {},
    printErr: (line: string) => stderr.push(line),
  });
  const instance = openscad.getInstance();

  // Mount only the closure (not the full libs/ tree).
  ensureDir(instance, "/libraries");
  for (const file of closure.files) {
    ensureParentDirs(instance, file.fsPath);
    instance.FS.writeFile(file.fsPath, file.source);
  }

  // Write the entry model and run.
  instance.FS.writeFile("/probe_input.scad", input.source);
  const args = [
    "/probe_input.scad",
    "-o", "/probe_output.stl",
    "--backend", "Manifold",
    ...(input.defines ?? []).flatMap((d) => d.split(" ")),
  ];

  let ok = false;
  let stl: Uint8Array | undefined;
  let errorMessage: string | undefined;
  try {
    const rc = instance.callMain(args);
    if (rc === 0) {
      const data = instance.FS.readFile("/probe_output.stl", { encoding: "binary" }) as Uint8Array;
      stl = data;
      ok = data.length > 0;
      if (!ok) errorMessage = "openscad produced empty STL";
    } else {
      errorMessage = `openscad exit=${rc}`;
    }
  } catch (e) {
    // Emscripten throws integer pointers on abort; stringify whatever
    // we got back. Common cause is a CSG operation that the manifold
    // backend can't handle (rare on Phase 0 corpus, but possible).
    errorMessage = `wasm aborted: ${e instanceof Error ? e.message : String(e)}`;
  }

  return {
    ok,
    stl,
    errorMessage,
    wallMs: performance.now() - t0,
    filesMounted: closure.files.length,
    missing: closure.missing,
    stderr,
  };
}

function ensureDir(instance: WasmInstance, path: string) {
  try { instance.FS.mkdir(path); } catch { /* exists */ }
}

function ensureParentDirs(instance: WasmInstance, fsPath: string) {
  const parts = fsPath.split("/").filter(Boolean);
  parts.pop(); // drop file name
  let acc = "";
  for (const p of parts) {
    acc += `/${p}`;
    ensureDir(instance, acc);
  }
}

interface WasmInstance {
  callMain: (args: string[]) => number;
  FS: {
    writeFile: (path: string, data: string | Uint8Array) => void;
    readFile: (path: string, opts?: { encoding: "utf8" | "binary" }) => string | Uint8Array;
    mkdir: (path: string) => void;
  };
}
