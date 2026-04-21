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

export interface ClosureFile {
  /** Path inside the Emscripten FS, e.g. `/libraries/BOSL2/std.scad`. */
  fsPath: string;
  source: string;
}

export interface ClosureResult {
  files: ClosureFile[];
  missing: string[];
  /** Number of unique includes resolved (excluding the entry file). */
  resolvedCount: number;
}

export type FileFetcher = (relPath: string) => Promise<string | null>;

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
  const { entrySource, fetchLibFile } = opts;
  const maxFiles = opts.maxFiles ?? 1500;

  const tried = new Set<string>();
  const resolved = new Set<string>();
  const files: ClosureFile[] = [];
  const missing: string[] = [];

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

  return { files, missing, resolvedCount: files.length };
}

/** Pull include/use targets out of one SCAD source. */
export function extractIncludes(source: string): string[] {
  const out: string[] = [];
  for (const m of source.matchAll(INCLUDE_USE_RE)) {
    out.push(m[1].trim());
  }
  return out;
}
