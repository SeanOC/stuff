// Native OpenSCAD render driver for the render service.
//
// The server (server.ts) shells out here to run a headless
// `openscad -o out.stl -D <defines> <model>` and returns a
// RenderResult-shaped object mirroring lib/wasm/render.ts so a later
// /api/export swap (Phase 2, st-rtb) maps one-to-one.
//
// Correctness is the whole point of this wrapper: OpenSCAD can exit 0
// and still have written a WRONG STL. Every guard below mirrors a bug
// the WASM path already learned the hard way:
//   - Exit 0 WITH a hard `ERROR:` logged => OpenSCAD dropped part of the
//     CSG tree and wrote partial geometry (st-7x7). Never a success.
//   - `WARNING: Can't open include/library/import '...'` => a missing
//     dependency renders silently absent (st-zph shipped a blower mount
//     with no blower body that way). Fatal, not a diagnostic.
//   - Empty STL => fail.
// Only a clean render (rc 0, no hard error, no unresolved dep, non-empty
// STL) ever returns ok:true with bytes.

import { spawn } from "node:child_process";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

export interface NativeRenderInput {
  /** Absolute path to the entry .scad (already validated + confined). */
  modelPath: string;
  /** `name=value` OpenSCAD defines; values already SCAD-literal-formatted. */
  defines: string[];
  /** OPENSCADPATH so vendored libs resolve (the baked libs/ root). */
  openscadPath: string;
  /** openscad binary (default "openscad"). */
  openscadBin?: string;
  /** Wrap in `xvfb-run -a` for hosts whose openscad wants a display. */
  xvfb?: boolean;
}

export interface NativeRenderResult {
  ok: boolean;
  stl?: Uint8Array;
  errorMessage?: string;
  /** Wall-clock ms for the whole render (spawn + read included). */
  wallMs: number;
  /** Captured stderr+stdout lines (warnings, errors, render summary). */
  stderr: string[];
  /** Render attempts made (> 1 when a CGAL-class error was retried). */
  attempts: number;
}

// First hard `ERROR:` line, or null. Mirrors lib/wasm/render.ts's
// hardErrorFrom — OpenSCAD logs a hard error, skips that node's
// geometry, and can still exit 0 with partial STL. Exit code alone is
// not a success signal.
export function hardErrorFrom(lines: string[]): string | null {
  return lines.find((l) => /^\s*ERROR\b/i.test(l)) ?? null;
}

// A "Can't open include/library/import '...'" warning means a
// dependency didn't resolve; OpenSCAD renders on without it. The
// unresolved target name is captured for the error message.
const CANT_OPEN_RE =
  /WARNING:\s*Can't open (?:include|library|import)(?:\s+file)?\s.*?'([^']+)'/i;

export function unresolvedFrom(lines: string[]): string[] {
  const out: string[] = [];
  for (const l of lines) {
    const m = l.match(CANT_OPEN_RE);
    if (m) out.push(m[1]);
  }
  return out;
}

// CGAL's convex_hull_3 (and friends) are randomized and have known
// robustness bugs on degenerate input — the same geometry can fail once
// and succeed on the next attempt. Mirrors lib/wasm/render.ts. Determin-
// istic errors (syntax, unknown identifiers) are not retried.
export function isRetryableError(errorLine: string): boolean {
  return /CGAL/i.test(errorLine);
}

const MAX_ATTEMPTS = 2;

export async function renderToStl(
  input: NativeRenderInput,
): Promise<NativeRenderResult> {
  const t0 = performance.now();
  const dir = await mkdtemp(path.join(tmpdir(), "render-"));
  const outStl = path.join(dir, "out.stl");

  let attempts = 0;
  let ok = false;
  let stl: Uint8Array | undefined;
  let errorMessage: string | undefined;
  let stderr: string[] = [];

  try {
    while (attempts < MAX_ATTEMPTS) {
      attempts += 1;
      const run = await runOpenscad(input, outStl);
      stderr = run.lines;

      const hardError = hardErrorFrom(run.lines);
      const unresolved = unresolvedFrom(run.lines);

      if (run.code !== 0) {
        errorMessage = hardError ?? `openscad exit=${run.code}`;
      } else if (hardError) {
        // Exit 0 with an ERROR logged: partial geometry (st-7x7).
        errorMessage = hardError.trim();
      } else if (unresolved.length > 0) {
        // Missing include/import: silently-absent geometry (st-zph).
        errorMessage = `unresolved dependency: ${unresolved.join(", ")}`;
      } else {
        const data = await readStl(outStl);
        if (data === null) {
          errorMessage = "openscad exited 0 but wrote no STL";
        } else if (data.length === 0) {
          errorMessage = "openscad produced an empty STL";
        } else {
          stl = data;
          ok = true;
          errorMessage = undefined;
        }
      }

      // Retry only a CGAL-class hard error with a fresh attempt; every
      // other outcome (success or deterministic failure) is final.
      if (ok || !hardError || !isRetryableError(hardError)) break;
    }
  } finally {
    await rm(dir, { recursive: true, force: true });
  }

  return { ok, stl, errorMessage, wallMs: performance.now() - t0, stderr, attempts };
}

interface RunResult {
  code: number;
  lines: string[];
}

function runOpenscad(input: NativeRenderInput, outStl: string): Promise<RunResult> {
  const bin = input.openscadBin ?? "openscad";
  const baseArgs = ["-o", outStl, ...input.defines.flatMap((d) => ["-D", d]), input.modelPath];
  const [cmd, args] = input.xvfb
    ? ["xvfb-run", ["-a", bin, ...baseArgs]]
    : [bin, baseArgs];

  return new Promise((resolve, reject) => {
    const child = spawn(cmd as string, args as string[], {
      env: { ...process.env, OPENSCADPATH: input.openscadPath },
    });
    // OpenSCAD emits WARNING/ERROR on stdout in some builds and stderr
    // in others; capture both so the guards see every line (mirrors
    // .claude/skills/_lib/openscad.py).
    const chunks: Buffer[] = [];
    child.stdout.on("data", (c: Buffer) => chunks.push(c));
    child.stderr.on("data", (c: Buffer) => chunks.push(c));
    child.on("error", reject);
    child.on("close", (code) => {
      const text = Buffer.concat(chunks).toString("utf8");
      const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
      resolve({ code: code ?? -1, lines });
    });
  });
}

async function readStl(outStl: string): Promise<Uint8Array | null> {
  try {
    return new Uint8Array(await readFile(outStl));
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw e;
  }
}
