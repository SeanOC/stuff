// Param-sweep connectivity guard (st-7x7).
//
// Renders every catalog model through the EXACT pipeline the site
// preview uses — parseScadParams -> applyParamOverrides -> renderToStl
// (openscad-wasm, Manifold backend) — at the min / mid / max of every
// numeric @param, both boolean states, and every enum choice, one
// param at a time from defaults. Each render must succeed with no hard
// ERROR, be watertight, and have exactly the expected number of
// connected components.
//
// Why this exists: a CSG failure inside the wasm engine can drop part
// of the tree yet still exit 0 with the partial geometry — the hex
// stylus shipped a shattered preview at hex_width=9 that desktop
// OpenSCAD never showed. Sweeping the param space through the real
// wasm path catches that class before it ships. The engine's CGAL
// failures are randomized (see lib/wasm/render.ts), so beyond the
// deterministic asserts, ~350 renders per run also act as a
// statistical fuzzer for intermittent trips.
//
// One param varies at a time; the combinatorial cross-product is
// intentionally NOT covered (it's unbounded), and neither are values
// off the @param grid. Runs via `npm run test:sweep` — too slow for
// the unit suite.

import { readFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  applyParamOverrides,
  defaultsOf,
  parseScadParams,
  type Param,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { renderToStl } from "@/lib/wasm/render";
import {
  connectedComponentCount,
  isWatertight,
  parseStlTriangles,
} from "@/lib/wasm/stl-analysis";
import { expectedComponents } from "./expectations";
import { KNOWN_FAILURES } from "./known-failures";

const ROOT = path.resolve(__dirname, "../..");
const PER_RENDER_TIMEOUT_MS = 300_000;

async function fetchLibFromDisk(relPath: string): Promise<string | null> {
  try {
    return await readFile(path.join(ROOT, "libs", relPath), "utf8");
  } catch {
    return null;
  }
}

export interface SweepCase {
  label: string;
  values: Record<string, ParamValue>;
}

/** Distinct sweep values for one param, excluding its default. */
function variantsOf(p: Param): ParamValue[] {
  switch (p.kind) {
    case "number":
    case "integer": {
      if (p.min === undefined || p.max === undefined) return [];
      const mid = snapMid(p);
      return [...new Set([p.min, mid, p.max])].filter((v) => v !== p.default);
    }
    case "boolean":
      return [!p.default];
    case "enum":
      return p.choices.filter((c) => c !== p.default);
    case "string":
      return []; // no meaningful sweep axis
  }
}

/** Midpoint of [min, max] snapped onto the param's step grid. */
function snapMid(p: Param & { kind: "number" | "integer" }): number {
  const raw = p.min! + (p.max! - p.min!) / 2;
  if (!p.step) return p.kind === "integer" ? Math.round(raw) : raw;
  const snapped = p.min! + Math.round((raw - p.min!) / p.step) * p.step;
  // Float-noise cleanup (0.30000000000000004 -> 0.3).
  return Number(snapped.toPrecision(12));
}

export function buildSweepCases(params: Param[]): SweepCase[] {
  const defaults = defaultsOf(params);
  const cases: SweepCase[] = [{ label: "defaults", values: defaults }];
  for (const p of params) {
    for (const v of variantsOf(p)) {
      cases.push({
        label: `${p.name}=${v}`,
        values: { ...defaults, [p.name]: v },
      });
    }
  }
  return cases;
}

/**
 * Register a describe() block sweeping one model. Call from a
 * per-model test file so vitest can run models in parallel workers.
 */
export function sweepModel(stem: string): void {
  const source = readFileSync(path.join(ROOT, "models", `${stem}.scad`), "utf8");
  const { params } = parseScadParams(source);
  const cases = buildSweepCases(params);

  describe(`param sweep: ${stem}`, () => {
    for (const c of cases) {
      // Pre-existing failures found when the guard first ran are
      // skipped with a bead reference, not deleted — see
      // known-failures.ts. it.skip rather than it.fails because
      // CGAL-class failures are randomized and would flake as
      // "unexpectedly passed".
      const knownFailure = KNOWN_FAILURES[stem]?.[c.label];
      const register = knownFailure ? it.skip : it;
      register(
        knownFailure ? `${c.label} — known failure, ${knownFailure}` : c.label,
        async () => {
          const res = await renderToStl({
            source: applyParamOverrides(source, params, c.values),
            fetchLibFile: fetchLibFromDisk,
          });
          const errTail = res.stderr.filter((l) => /error/i.test(l)).slice(0, 4).join(" | ");
          expect(res.ok, `render failed: ${res.errorMessage ?? "?"} ${errTail}`).toBe(true);

          const tris = parseStlTriangles(res.stl!);
          expect(tris.length, "empty mesh").toBeGreaterThan(0);
          expect(isWatertight(tris), "mesh is not watertight").toBe(true);

          const expected = expectedComponents(stem, c.values);
          if (expected !== null) {
            expect(
              connectedComponentCount(tris),
              `connected-component count drifted (expected ${expected})`,
            ).toBe(expected);
          }
        },
        PER_RENDER_TIMEOUT_MS,
      );
    }
  });
}
