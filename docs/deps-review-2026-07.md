# Dependency review — July 2026 (st-gbx)

Full survey of every library the project consumes, against upstream as of
2026-07-11. Three inventories: vendored OpenSCAD libs, npm packages, and
the WASM render engine. Verdicts: **safe** (applied), **hold** (documented
reason, follow-up filed where worthwhile), **no-change** (already current).

## 1. Vendored OpenSCAD libraries

Pins live in `libs/README.md`; `scripts/vendor-libs.sh` clones them (plus
local patches under `scripts/patches/`). Upstream state checked via fresh
clones on 2026-07-11.

| Library | Pinned | Upstream HEAD | Behind | Verdict |
|---|---|---|---|---|
| BOSL2 | `456fcd8` (2024-09-22) | `fbcdfdd` v2.0.747 (2026-06-29) | 1393 commits | **hold** — st-kls incompatibility still live, see below |
| QuackWorks | `6123129` (2026-02-03) | `6123129` | 0 | **no-change** — pin *is* HEAD; local click-hole patch still required |
| gridfinity-rebuilt-openscad | `910e22d` (2025-08-31) | `910e22d` | 0 | **no-change** |
| NopSCADlib | `c9baa0e` (2025-10-08) | `c9baa0e` | 0 | **no-change** (documented pin only — not vendored, no model uses it) |
| threads-scad | `4ae9aeb` (2021-12-01) | `4ae9aeb` | 0 | **no-change** (dormant upstream; documented pin only) |
| MCAD | `bd0a7ba` (2021-10-25) | `bd0a7ba` | 0 | **no-change** (dormant upstream; documented pin only) |

Only BOSL2, QuackWorks, and gridfinity-rebuilt are actually vendored and
used by models (`grep` over `models/*.scad`). NopSCADlib / threads-scad /
MCAD rows in `libs/README.md` are an available-libraries menu, not active
dependencies — nothing to gate.

### BOSL2 hold (st-kls, re-verified 2026-07-11) — SUPERSEDED 2026-07-21

> **Superseded by pst-9sw.** The pin is now `fbcdfdd5` (v2.0.747). The hold
> below was dissolved not by patching the vector-spin call sites it names,
> but by dropping both files that contain them: `snapConnector.scad` was
> already unused, and the 2 shipped models moved to QuackWorks' BOSL2-free
> copy of the same backer, `Modules/multiconnectSlotDesign.scad`. Nothing in
> the catalog reaches a vector-spin site now. See `libs/README.md`.
> The analysis below is kept as the record of why the pin was held.

The pin was rolled back from `663cd7c` to `456fcd8` on 2026-04-17 (st-kls)
because BOSL2 PR #1475 tightened `attachable()` to assert
`is_finite(spin)`, rejecting the `spin=[x,y,z]` vector syntax QuackWorks
uses. Re-checked both sides at current HEADs:

- BOSL2 `fbcdfdd` `attachments.scad` still asserts finite spin at 5 sites
  (lines 579, 963, 2444, 2624, 3244).
- QuackWorks HEAD (== our pin) still passes vector spin at
  `Modules/snapConnector.scad:59` (`spin=[0,270,0]`) and
  `Modules/multiconnectSlotDesignBOSL.scad:140` (`spin=[90,0,0]`).
  `multiconnectSlotDesignBOSL.scad` is used by 2 shipped models.

The incompatibility is unchanged, so the pin stands. A future path would
be a local QuackWorks patch rewriting the vector-spin call sites (the
`scripts/patches/` infrastructure from st-79a makes this mechanical), but
that trades a known-good pin for a 21-month, 1393-commit engine-adjacent
jump — BOSL2's rounding/hull internals are exactly the code implicated in
the wasm CGAL assert class (st-7x7/st-79a). Not worth it while nothing we
need is missing at `456fcd8`.

### QuackWorks notes

- st-79a's bead notes cite upstream HEAD as `4f34fce` — that was stale;
  `4f34fce` (2025-10-01, slicer split-to-objects fix #102) is 18 commits
  **behind** our pin, so that fix is already in our tree.
- Upstream has still not fixed the hull-rounded click holes, so
  `scripts/patches/QuackWorks/0001-opengrid-snap-linear-extrude-click-holes.patch`
  stays.
- License remains CC BY-NC-SA 4.0 (no commercial use of derived parts).

## 2. WASM render engine

**`openscad-wasm-prebuilt@1.2.0` — no-change; no newer release exists.**

The bead flagged this as high interest (a newer engine might obsolete the
st-7x7/st-79a CGAL `convex_hull_3.h:684` assert workarounds). Findings:

- 1.2.0 (2025-01-22) is the newest version on npm (`npm view ... versions`).
- The source repo (`lorenzowritescode/openscad-wasm`) is dormant: HEAD is
  the v1.2.0 tag itself, no commits since January 2025.

There is no newer engine to test against the known-failure cases, so the
workarounds stand on their own merits (st-79a's patch already cleared the
openGrid entries from `tests/sweep/known-failures.ts`; the remaining
entries are model-level param-extreme bugs tracked by st-dlu/st-ti3/
st-38y/st-1us/st-344/st-9hn, not engine bugs). If the engine ever matters
again, candidates are building from `openscad/openscad-wasm` upstream or
the openscad-playground builds — deliberately not pursued here.

## 3. npm packages

Baseline before changes: vitest 209/209, `next build` clean, playwright
44 passed / 1 skipped. Same gates re-run green after **each** batch below.
Model-pipeline gates (full export, invariants, param sweep) are not
applicable to these bumps — no `.scad`, `libs/`, or engine change — but a
sweep smoke file was run green on the final state anyway.

### Applied (3 commits, one batch each)

| Package | From | To | Batch |
|---|---|---|---|
| next | 16.2.4 | 16.2.10 | A — runtime |
| react / react-dom | 19.2.5 | 19.2.7 | A |
| @types/react | 19.2.14 | 19.2.17 | A |
| @types/node | 22.19.17 | 22.20.1 | A (holding the 22 line — CI runs Node 22) |
| tailwindcss / @tailwindcss/postcss | 4.2.4 | 4.3.2 | B — styling |
| postcss | 8.5.10 | 8.5.16 | B |
| @playwright/test | 1.59.1 | 1.61.1 | C — tooling |
| jsdom | 29.0.2 | 29.1.1 | C |
| @vercel/blob | 2.5.0 | 2.6.1 | C |
| undici (transitive, under jsdom) | 7.25.0 | 7.28.0 | C (`npm audit fix`) |

### Held

| Package | Current | Latest | Why held |
|---|---|---|---|
| three + @types/three | 0.169.0 | 0.185.1 | three breaks APIs per minor; drives StlViewer. Needs its own migration pass with visual verification. **Follow-up: st-3js.** |
| vitest | 2.1.9 | 4.1.10 | Two majors; vitest runs both unit tests and the param-sweep guard. Dev-only, but it carries the audit's critical advisory — worth doing deliberately. **Follow-up: st-35j.** |
| typescript | 5.9.3 | 7.0.2 | TS 6/7 (native compiler) are fresh majors; range pins `^5.6.0`. Revisit once Next/ecosystem support settles. No bead — routine future bump. |
| @types/node | 22.20.1 | 26.x | Tracks the runtime; CI is on Node 22. Bump alongside a Node upgrade, not independently. |
| @vercel/config | 0.2.1 | 0.5.5 | Upgrading does **not** clear its audit advisory (all `>=0.0.33` depend on vulnerable `@vercel/routing-utils`/`path-to-regexp`; npm's "fix" is a downgrade to 0.0.32). Usage is one typed `framework: "nextjs"` export; dev-only. Zero benefit, 0.x API churn risk. |

Already current (not in `npm outdated`): clsx 2.1.1,
google-auth-library 10.9.0, @testing-library/react 16.3.2,
@types/react-dom 19.2.3, openscad-wasm-prebuilt 1.2.0 (pinned exact).

### npm audit posture (post-review: 10 advisories — 5 moderate, 4 high, 1 critical)

All remaining advisories are dev-only or upstream-owned; none is
actionable by a safe bump:

- **vitest 2.x chain** (1 critical on vitest itself + esbuild/vite/
  vite-node moderates/high): test runner only, never ships. Fix = vitest 4
  → st-35j.
- **@vercel/config chain** (high, path-to-regexp ReDoS): dev-only typed
  config; no fixed-forward version exists (see table above).
- **next → bundled postcss** (moderate): inside next's own
  `node_modules`; npm's suggested "fix" is a downgrade to next@9. Noise —
  next's bundled copy is upstream's to bump.
- **undici@6.27.0 under @vercel/blob**: outside the advisory's affected
  range (7.0.0–7.27.2); flagged only as informational tree noise.
