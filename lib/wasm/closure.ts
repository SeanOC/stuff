// Walks a SCAD source's `include`/`use` graph and returns the minimal
// set of library files needed to render it. The harness in
// experiments/wasm-spike/ mounted all 576 lib files and paid 60s of
// parse time; mounting only the closure should bring that down by an
// order of magnitude (per st-556 Phase 0 findings).
//
// Resolution rule mirrors OpenSCAD: paths in `include <...>` /
// `use <...>` are resolved against the OPENSCAD library root
// (here, `/libraries/`), then against the directory of the file that
// did the include.
//
// fetchFile(path) is host-supplied so this works in both the browser
// (fetch from /api/source) and Node (read from disk in tests).

const INCLUDE_USE_RE = /^\s*(?:include|use)\s*<\s*([^>]+?)\s*>/gm;

// import("file.stl") / import(file = "file.stl") in the ENTRY source
// only — lib files are not scanned (their import()s, if any, live in
// demo code we never execute). The path must be a literal string for
// the walker to see it. Line-start guard keeps `// import("x")`
// comments from matching.
const IMPORT_RE = /^\s*[^/\n]*\bimport\s*\(\s*(?:file\s*=\s*)?"([^"]+)"/gm;

export interface ClosureFile {
  /** Path inside the Emscripten FS, e.g. `/libraries/BOSL2/std.scad`. */
  fsPath: string;
  source: string;
}

export interface ClosureAsset {
  /**
   * Path inside the Emscripten FS. The entry is written to the FS
   * root, so a relative import("x.stl") resolves to /x.stl.
   */
  fsPath: string;
  data: Uint8Array;
}

export interface ClosureResult {
  files: ClosureFile[];
  /** Binary files (STL meshes) referenced by entry-level import(). */
  assets: ClosureAsset[];
  missing: string[];
  /** Number of unique includes resolved (excluding the entry file). */
  resolvedCount: number;
}

export type FileFetcher = (relPath: string) => Promise<string | null>;

/**
 * Resolves a models/-relative path (e.g. "ego_lb6500_blower_mount.stl")
 * to binary content, or null if not found. Import paths in a model are
 * relative to the model's own directory — models/ on the host.
 */
export type AssetFetcher = (relPath: string) => Promise<Uint8Array | null>;

export interface BuildClosureOpts {
  /** SCAD source for the entry model. */
  entrySource: string;
  /**
   * Path the entry source will be written to in the FS. Used to
   * resolve relative includes from the entry's directory.
   * Default: "/probe_input.scad" (a sibling of /libraries).
   */
  entryFsPath?: string;
  /** Returns lib-relative SCAD source, or null if not found. */
  fetchLibFile: FileFetcher;
  /**
   * Returns models/-relative binary content for entry-level import()
   * targets. Optional: when absent, import() targets are reported as
   * missing instead of fetched.
   */
  fetchAssetFile?: AssetFetcher;
  /** Hard cap; defaults to 1500. Catches accidental cycles + bad libs. */
  maxFiles?: number;
}

/**
 * Resolve the `include`/`use` closure of `entrySource`. Returns the
 * full set of library files (paths under /libraries/) plus a missing
 * list for diagnostics. Cycles are handled — each path is visited
 * once.
 */
export async function buildIncludeClosure(
  opts: BuildClosureOpts,
): Promise<ClosureResult> {
  const { entrySource, fetchLibFile, fetchAssetFile } = opts;
  const maxFiles = opts.maxFiles ?? 1500;

  const tried = new Set<string>();
  const resolved = new Set<string>();
  const files: ClosureFile[] = [];
  const assets: ClosureAsset[] = [];
  const missing: string[] = [];

  // Binary assets referenced by entry-level import(). The entry lands
  // at the FS root, so each asset mounts at /<rel> for OpenSCAD's
  // relative-to-importing-file resolution to find it.
  for (const rel of extractImports(entrySource)) {
    const data = fetchAssetFile ? await fetchAssetFile(rel) : null;
    if (data === null) {
      missing.push(rel);
    } else {
      assets.push({ fsPath: `/${rel}`, data });
    }
  }

  // Queue items are ordered candidate lists for a single logical
  // include: we try the lib-root path first, then the sibling path.
  // An include counts as "missing" only if every candidate fails.
  const queue: string[][] = [];
  for (const rel of extractIncludes(entrySource)) queue.push([rel]);

  while (queue.length > 0 && files.length < maxFiles) {
    const candidates = queue.shift()!;
    if (candidates.some((c) => resolved.has(c))) continue;

    let loaded: { rel: string; source: string } | null = null;
    for (const rel of candidates) {
      if (tried.has(rel)) continue;
      tried.add(rel);
      const source = await fetchLibFile(rel);
      if (source !== null) {
        loaded = { rel, source };
        break;
      }
    }

    if (!loaded) {
      missing.push(candidates[0]);
      continue;
    }
    resolved.add(loaded.rel);

    files.push({ fsPath: `/libraries/${loaded.rel}`, source: loaded.source });

    // For each child include, resolve as-is first (lib-root), then
    // relative to the current file's directory. OpenSCAD tries both.
    const childDir = loaded.rel.includes("/")
      ? loaded.rel.slice(0, loaded.rel.lastIndexOf("/"))
      : "";
    for (const childRel of extractIncludes(loaded.source)) {
      const childCandidates = childDir
        ? [childRel, `${childDir}/${childRel}`]
        : [childRel];
      queue.push(childCandidates);
    }
  }

  return { files, assets, missing, resolvedCount: files.length };
}

/** Pull include/use targets out of one SCAD source. */
export function extractIncludes(source: string): string[] {
  const out: string[] = [];
  for (const m of source.matchAll(INCLUDE_USE_RE)) {
    out.push(m[1].trim());
  }
  return out;
}

/** Pull literal-string import() targets out of one SCAD source, deduped. */
export function extractImports(source: string): string[] {
  const out = new Set<string>();
  for (const m of source.matchAll(IMPORT_RE)) {
    out.add(m[1].trim());
  }
  return [...out];
}
