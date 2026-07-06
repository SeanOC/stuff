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

import {
  buildIncludeClosure,
  type AssetFetcher,
  type FileFetcher,
} from "./closure";

export interface RenderInput {
  /** SCAD source for the entry model. */
  source: string;
  /** Resolves a lib-relative path like "BOSL2/std.scad" to source. */
  fetchLibFile: FileFetcher;
  /**
   * Resolves a models/-relative binary path (entry-level import()
   * target, e.g. an STL mesh) to bytes. Only needed for models that
   * import() — omitting it makes those renders fail with the import
   * reported in `missing`.
   */
  fetchAssetFile?: AssetFetcher;
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
  /** Render attempts made (> 1 when a CGAL-class error was retried). */
  attempts: number;
}

/**
 * First hard `ERROR:` line in stderr, or null. OpenSCAD can log a hard
 * error (e.g. a CGAL failure inside one CSG node), skip that node's
 * geometry, and still exit 0 with a non-empty STL of whatever remained
 * — st-7x7 shipped a shattered preview exactly that way. Exit code and
 * STL presence alone are therefore not a success signal.
 */
export function hardErrorFrom(stderr: string[]): string | null {
  return stderr.find((line) => /^\s*ERROR\b/i.test(line)) ?? null;
}

/**
 * CGAL's convex_hull_3 (and friends) are randomized algorithms with
 * known robustness bugs on degenerate input in the wasm build's CGAL
 * version — the same geometry can fail on one render and succeed on
 * the next (st-7x7). One retry with a fresh instance is cheap and
 * usually lands a good insertion order. Deterministic errors (syntax,
 * unknown identifiers) are not retried.
 */
export function isRetryableError(errorLine: string): boolean {
  return /CGAL/i.test(errorLine);
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
      fetchAssetFile: input.fetchAssetFile,
    });
  } catch (e) {
    return {
      ok: false,
      errorMessage: `closure walk failed: ${e instanceof Error ? e.message : String(e)}`,
      wallMs: performance.now() - t0,
      filesMounted: 0,
      missing: [],
      stderr,
      attempts: 0,
    };
  }

  const { createOpenSCAD } = await loadModule();
  const args = [
    "/probe_input.scad",
    "-o", "/probe_output.stl",
    "--backend", "Manifold",
    ...(input.defines ?? []).flatMap((d) => d.split(" ")),
  ];

  const MAX_ATTEMPTS = 2;
  let attempts = 0;
  let ok = false;
  let stl: Uint8Array | undefined;
  let errorMessage: string | undefined;

  while (attempts < MAX_ATTEMPTS) {
    attempts += 1;
    stderr.length = 0; // report only the deciding attempt's log

    // Fresh instance per attempt: emscripten's runtime isn't built for
    // repeated callMain, and a retry only helps CGAL's randomized
    // algorithms if it starts from a clean slate.
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
    // Binary import() assets mount at the FS root, siblings of the
    // entry, so relative import paths resolve.
    for (const asset of closure.assets) {
      ensureParentDirs(instance, asset.fsPath);
      instance.FS.writeFile(asset.fsPath, asset.data);
    }

    // Write the entry model and run.
    instance.FS.writeFile("/probe_input.scad", input.source);

    try {
      const rc = instance.callMain(args);
      const hardError = hardErrorFrom(stderr);
      if (rc !== 0) {
        errorMessage = hardError ?? `openscad exit=${rc}`;
      } else if (hardError) {
        // Exit 0 with an ERROR logged means OpenSCAD dropped part of
        // the CSG tree and wrote partial geometry — never show that
        // as a successful render.
        errorMessage = hardError.trim();
      } else {
        const data = instance.FS.readFile("/probe_output.stl", { encoding: "binary" }) as Uint8Array;
        stl = data;
        ok = data.length > 0;
        errorMessage = ok ? undefined : "openscad produced empty STL";
      }
      if (ok || !hardError || !isRetryableError(hardError)) break;
    } catch (e) {
      // Emscripten throws integer pointers on abort; stringify whatever
      // we got back. Common cause is a CSG operation that the manifold
      // backend can't handle (rare on Phase 0 corpus, but possible).
      errorMessage = `wasm aborted: ${e instanceof Error ? e.message : String(e)}`;
      break;
    }
  }

  return {
    ok,
    stl,
    errorMessage,
    wallMs: performance.now() - t0,
    filesMounted: closure.files.length,
    missing: closure.missing,
    stderr,
    attempts,
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
