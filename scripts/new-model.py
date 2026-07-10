#!/usr/bin/env python3
"""Scaffold a new parametric model: all four required artifacts at once.

Usage: scripts/new-model.py <stem> --category <id> [--blurb TEXT] [--opengrid]
  e.g. scripts/new-model.py widget_hook_20mm --category household

Generates the complete artifact set a model needs to surface in the
gallery and pass the repo gates (st-t71):

  models/<stem>.scad             param-annotated skeleton (renders as-is)
  models/<stem>.invariants.py    sidecar stub with the standard asserts
  tests/sweep/<stem>.test.ts     param-sweep registration (coverage.test.ts
                                 fails without it)
  lib/models/catalog.ts          CATALOG entry appended (listModels()
                                 THROWS on a missing entry — models
                                 without one silently never surface)

--opengrid emits the openGrid wall-mount conventions instead of a plain
body: 28mm-pitch directional snap grid (strong nub up), the vendored
openGridSnap() wrapped with the root-fillet weld shims (st-v7k), and a
snap-pitch invariant pinning the bed-contact span.

Idempotent and refuses to clobber: if ANY target artifact (or the
catalog key) already exists, nothing is written and the collisions are
listed. Valid categories are parsed from MODEL_CATEGORIES in
lib/models/catalog.ts, never hardcoded here.

Conventions encoded here are derived from the existing models — see
.claude/skills/new-model/SKILL.md for the authoring checklist that
picks up where the scaffold stops.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

STEM_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# --- catalog.ts parsing -------------------------------------------------

def parse_categories(catalog_src: str) -> list[str]:
    """Category ids from the MODEL_CATEGORIES block (source of truth)."""
    block = re.search(
        r"MODEL_CATEGORIES\s*=\s*\[(.*?)\]\s*as\s+const", catalog_src, re.S
    )
    if not block:
        raise ValueError("MODEL_CATEGORIES block not found in catalog.ts")
    ids = re.findall(r'id:\s*"([^"]+)"', block.group(1))
    if not ids:
        raise ValueError("no category ids found in MODEL_CATEGORIES")
    return ids


def parse_catalog_keys(catalog_src: str) -> list[str]:
    block = re.search(
        r"export const CATALOG[^=]*=\s*\{(.*)^\};", catalog_src, re.S | re.M
    )
    if not block:
        raise ValueError("CATALOG block not found in catalog.ts")
    return re.findall(r"^  ([A-Za-z0-9_]+):\s*\{", block.group(1), re.M)


def insert_catalog_entry(
    catalog_src: str, stem: str, category: str, blurb: str
) -> str:
    """Append an entry before the CATALOG block's closing `};`."""
    start = re.search(r"export const CATALOG[^=]*=\s*\{", catalog_src)
    if not start:
        raise ValueError("CATALOG block not found in catalog.ts")
    # Entries close at two-space indent (`  },`), so the first `\n};`
    # after the opening brace is the block's own closer.
    close = catalog_src.find("\n};", start.end())
    if close == -1:
        raise ValueError("could not locate CATALOG closing brace in catalog.ts")
    escaped = blurb.replace("\\", "\\\\").replace('"', '\\"')
    entry = (
        f"  {stem}: {{\n"
        f'    categoryId: "{category}",\n'
        f"    blurb:\n"
        f'      "{escaped}",\n'
        f"  }},\n"
    )
    return catalog_src[: close + 1] + entry + catalog_src[close + 1 :]


# --- templates ----------------------------------------------------------

def scad_plain(stem: str) -> str:
    return f'''\
// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// TODO({stem}): one-line description. This first prose comment line
// becomes the gallery title (lib/models/discover.ts skips the SPDX and
// Copyright lines and takes the next `//` line).
//
// === Print orientation (native): TODO ===
//
// Document the print orientation and the zero-supports story (what
// touches the bed, why every overhang is safe). House style exemplar:
// models/opengrid_panel_aligner.scad.

include <BOSL2/std.scad>

$fn = 64;

// === User-tunable parameters ===

width  = 60;  // @param number min=20 max=200 step=1 unit=mm group=body label="Width (X)"
depth  = 40;  // @param number min=20 max=200 step=1 unit=mm group=body label="Depth (Y)"
height = 10;  // @param number min=2 max=100 step=0.5 unit=mm group=body label="Height (Z)"

// @preset id="default" label="Default" width=60 depth=40 height=10

// === Derived ===

// Zero-overlap (face-kissing) unions leave detached shells or
// non-manifold tangent edges (st-v7k class): sink joined solids this
// far into each other instead of butting faces.
bury = 0.6;

// PRINT_ANCHOR_BBOX at defaults (keep the arithmetic comment current —
// the invariants gate fails on >1mm drift from the exported STL):
//   X = width  = 60
//   Y = depth  = 40
//   Z = height = 10
PRINT_ANCHOR_BBOX = [60, 40, 10];

// === Body ===

// TODO({stem}): replace the placeholder solid with the real model.
// Rounding style: NO hull-backed rounding (BOSL2 cuboid rounding=/
// edges= on 3D ops) — the wasm engine's CGAL applyHull() asserts on
// some swept dimensions (st-7x7/st-560 class). Round vertical edges as
// extruded 2D rect(rounding=) footprints; chamfer exposed rims with
// explicit 45deg prisms that overshoot past the faces they cut
// (st-n4v: coplanar cut faces are degenerate booleans).

cuboid([width, depth, height], anchor = BOT);
'''


def scad_opengrid(stem: str) -> str:
    return f'''\
// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// TODO({stem}): one-line description. This first prose comment line
// becomes the gallery title (lib/models/discover.ts skips the SPDX and
// Copyright lines and takes the next `//` line).
//
// LICENSING: the openGrid snap comes from QuackWorks
// (libs/QuackWorks/openGrid/opengrid-snap.scad, openGrid by David D,
// OpenSCAD port by metasyntactic), licensed CC BY-NC-SA 4.0 —
// NON-COMMERCIAL. This derived model is for personal use only; do not
// sell prints or files.
//
// === Print orientation (native): ZERO supports ===
//
// Prints snaps-down: the snap faces are the first layers — the
// orientation the snap geometry was designed to print in (nubs and
// click slots all form correctly). Bed contact is the 24.8mm snap
// faces. TODO({stem}): as you add body geometry, keep every overhang a
// 45deg chamfer, never a flat span, and keep the 3.2mm channels
// between snaps clear — slicer support in there is near-impossible to
// dig out.
//
// === Wall-hang orientation / load direction ===
//
// Directional snaps with the strong front nub (non-flexing, 0.8mm deep
// vs 0.4) pointing +Y — up the wall — so lever-out load bears on the
// rigid hook and the flexy click-in side faces down (st-0of rationale,
// same as ego_lb6500_blower_mount / opengrid_bin). For a tool that
// clicks in and pulls straight out, switch to directional = false
// (see opengrid_panel_aligner).

include <BOSL2/std.scad>
// `use` not `include`: opengrid-snap.scad ends with a top-level demo
// call that would otherwise inject a stray snap into every render.
use <QuackWorks/openGrid/opengrid-snap.scad>

$fn = 64;

// === User-tunable parameters ===

width_units  = 2;     // @param integer min=1 max=6 step=1 group=grid label="Width (28mm openGrid tiles)"
height_units = 2;     // @param integer min=1 max=6 step=1 group=grid label="Height (28mm openGrid tiles)"
snap_lite    = false; // @param boolean group=grid label="Lite snaps (3.4mm instead of 6.8mm)"
plate_t      = 4;     // @param number min=3 max=6 step=0.5 unit=mm group=plate label="Back plate thickness"

// @preset id="default" label="Default (2x2 tiles, full snaps)" width_units=2 height_units=2 snap_lite=false plate_t=4

// === Derived ===

snap_pitch = 28;    // openGrid tile pitch
snap_w     = 24.8;  // snap footprint
snap_h     = snap_lite ? 3.4 : 6.8;
weld       = 0.02;  // embed depth of snap tops into the plate (st-v7k)
// Walls/posts sink this far into the solid below them. Zero-overlap
// (face-kissing) unions leave detached shells / non-manifold tangent
// edges (st-v7k class).
bury = 0.6;

// Plate sized in whole tiles so the mounted part aligns with the grid
// (opengrid_bin convention). Frame: XY centered on the snap array,
// z = 0 on the bed at the snap faces.
plate_w   = width_units * snap_pitch;
plate_d   = height_units * snap_pitch;
plate_z0  = snap_h - weld;
plate_top = plate_z0 + plate_t;

// PRINT_ANCHOR_BBOX at defaults (keep the arithmetic comment current —
// the invariants gate fails on >1mm drift from the exported STL):
//   X = plate_w   = 2 * 28              = 56
//   Y = plate_d   = 2 * 28              = 56
//   Z = plate_top = 6.8 - 0.02 + 4      = 10.78
PRINT_ANCHOR_BBOX = [56, 56, 10.78];

// === Snaps ===

// One openGrid snap in its own frame (front/strong nub toward +X),
// welded into a single solid — verbatim from ego_lb6500_blower_mount
// (st-0of), where it's verified watertight + single-component for both
// snap depths. openGridSnap models its click nubs as face-touching
// solids whose root tangent line survives as a non-2-manifold edge;
// each 0.3mm shim straddles a nub/core contact plane (local x=12.4)
// and volumetrically fuses nub to core on both CGAL and Manifold. The
// 14mm-wide front nub's shim widens to 14.6; the rear nub's sits 0.65
// higher (its root rides above the base band in the directional
// variant). NEVER re-derive snap geometry — the browser pipeline can
// only resolve vendored libs/, so this wrapper is kept textually
// identical across models: fix a bug here, apply it to the siblings.
module welded_directional_snap() {{
    base   = snap_lite ? 0 : 3.4;
    root_z = max(0, base - 0.01);
    root_h = snap_lite ? 0.61 : 0.62;
    openGridSnap(lite = snap_lite, directional = true,
                 anchor = BOT, orient = UP, spin = 0);
    for (a = [90, 270])                       // side nubs
        zrot(a) translate([12.4, 0, root_z])
            cuboid([0.3, 11.6, root_h], anchor = BOT);
    translate([12.4, 0, root_z])              // front (strong) nub
        cuboid([0.3, 14.6, root_h], anchor = BOT);
    zrot(180) translate([12.4, 0, base + 0.64])  // rear (click) nub
        cuboid([0.3, 11.6, 0.62], anchor = BOT);
}}

// One snap per tile on the 28mm pitch. zrot(90) turns each snap's
// strong front nub toward +Y — up the wall.
module grid_snaps() {{
    for (cx = [0 : width_units - 1], ry = [0 : height_units - 1])
        translate([(cx - (width_units - 1) / 2) * snap_pitch,
                   (ry - (height_units - 1) / 2) * snap_pitch,
                   0])
            zrot(90) welded_directional_snap();
}}

// === Body ===

// TODO({stem}): grow the real model out of the back plate (hooks,
// pockets, cradles...). Rounding style: NO hull-backed rounding (BOSL2
// cuboid rounding=/edges= on 3D ops) — the wasm engine's CGAL
// applyHull() asserts on some swept dimensions (st-7x7/st-560 class).
// Round vertical edges as extruded 2D rect(rounding=) footprints;
// chamfer exposed rims with explicit 45deg prisms.

union() {{
    grid_snaps();
    translate([0, 0, plate_z0])
        cuboid([plate_w, plate_d, plate_t], anchor = BOT);
}}
'''


def invariants_plain(stem: str) -> str:
    return f'''\
"""Invariants for {stem}.

TODO({stem}): replace this docstring with the numbered structural
claims the model exists for (footprint, clearances, retention
geometry, orientation) and assert them in check() below.

Built-ins run automatically for every model — watertight, orphan
fragments, triangle ceiling, PRINT_ANCHOR_BBOX drift, preset validity
(scripts/invariants/__init__.py) — so only assert what THIS model
specifically claims.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # Topology pin: one printed solid. Multi-body models pass the
    # expected count instead (compute it from params when it varies,
    # and keep tests/sweep/expectations.ts in sync).
    failures.extend(expect_connected_solids(ctx, 1))

    # TODO({stem}): assert the model's real claims, e.g.:
    # if ctx["bbox_mm"][2] > 250:
    #     failures.append(Failure("envelope", "Z > 250mm; won't fit the X1C bed"))

    return failures
'''


def invariants_opengrid(stem: str) -> str:
    return f'''\
"""Invariants for {stem}.

TODO({stem}): replace this docstring with the numbered structural
claims the model exists for. The snap-grid asserts below are the
standard openGrid set (opengrid_bin convention); keep them.

Built-ins run automatically for every model — watertight, orphan
fragments, triangle ceiling, PRINT_ANCHOR_BBOX drift, preset validity
(scripts/invariants/__init__.py) — so only assert what THIS model
specifically claims.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # Topology pin: snaps + plate weld into one printed solid. If the
    # QuackWorks or BOSL2 pin moves and the root-fillet shims stop
    # landing inside the click nubs, the component count breaks first.
    failures.extend(expect_connected_solids(ctx, 1))

    width_units = int(p.get("width_units", 2))
    height_units = int(p.get("height_units", 2))

    # Bed contact spans exactly the snap grid: one snap per tile on the
    # 28mm pitch. Pins both pitch and count, and proves the snaps-down
    # print orientation (z=0 at the snap faces).
    verts = ctx["stl"].vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        ))
        return failures
    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (width_units - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (height_units - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {{span_x:.1f}} x {{span_y:.1f}}mm but a "
            f"{{width_units}}x{{height_units}} snap grid on the 28mm pitch "
            f"should span {{want_x:.1f}} x {{want_y:.1f}}mm — snap count or "
            f"pitch drifted",
        ))

    # TODO({stem}): assert the body's real claims (footprint, shell
    # thickness bounds, open-cavity probes via ctx["stl"].contains).

    return failures
'''


def sweep_test(stem: str) -> str:
    return f'import {{ sweepModel }} from "./runner";\n\nsweepModel("{stem}");\n'


# --- main ---------------------------------------------------------------

def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Scaffold a new parametric model (all four artifacts)."
    )
    p.add_argument("stem", help="model stem, e.g. widget_hook_20mm (snake_case)")
    p.add_argument(
        "--category",
        required=True,
        help="categoryId from MODEL_CATEGORIES in lib/models/catalog.ts",
    )
    p.add_argument(
        "--blurb",
        default=None,
        help="1-2 sentence gallery blurb (default: a TODO placeholder)",
    )
    p.add_argument(
        "--opengrid",
        action="store_true",
        help="openGrid wall-mount skeleton: 28mm directional snap grid, "
        "welded openGridSnap wrapper, snap-pitch invariants",
    )
    p.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repo root to scaffold into (tests use a sandbox tree)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    stem = args.stem
    root = args.root.resolve()

    if not STEM_RE.match(stem):
        print(
            f"error: stem '{stem}' must be snake_case "
            "([a-z][a-z0-9_]*) — it becomes the .scad filename, catalog "
            "key, and URL slug",
            file=sys.stderr,
        )
        return 1

    catalog_path = root / "lib" / "models" / "catalog.ts"
    if not catalog_path.is_file():
        print(f"error: {catalog_path} not found — wrong --root?", file=sys.stderr)
        return 1
    catalog_src = catalog_path.read_text()

    try:
        categories = parse_categories(catalog_src)
        existing_keys = parse_catalog_keys(catalog_src)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.category not in categories:
        print(
            f"error: unknown category '{args.category}'. Valid ids "
            f"(from MODEL_CATEGORIES in lib/models/catalog.ts): "
            f"{', '.join(categories)}",
            file=sys.stderr,
        )
        return 1

    targets = {
        root / "models" / f"{stem}.scad": (
            scad_opengrid(stem) if args.opengrid else scad_plain(stem)
        ),
        root / "models" / f"{stem}.invariants.py": (
            invariants_opengrid(stem) if args.opengrid else invariants_plain(stem)
        ),
        root / "tests" / "sweep" / f"{stem}.test.ts": sweep_test(stem),
    }

    collisions = [str(p.relative_to(root)) for p in targets if p.exists()]
    if stem in existing_keys:
        collisions.append(f"lib/models/catalog.ts key '{stem}'")
    if collisions:
        print(
            "error: refusing to clobber existing artifacts for "
            f"'{stem}':\n  " + "\n  ".join(collisions),
            file=sys.stderr,
        )
        return 1

    blurb = args.blurb or (
        f"TODO({stem}): 1-2 sentence gallery blurb — what it holds/mounts, "
        "the key dimension, the print story."
    )
    new_catalog = insert_catalog_entry(catalog_src, stem, args.category, blurb)

    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    catalog_path.write_text(new_catalog)

    rel = [str(p.relative_to(root)) for p in targets]
    print(
        "Created:\n  "
        + "\n  ".join(rel)
        + "\n  lib/models/catalog.ts (entry appended)\n\n"
        "Next steps (full checklist: .claude/skills/new-model/SKILL.md):\n"
        f"  1. Replace the TODO body + header prose in models/{stem}.scad\n"
        f"  2. Render + eyeball: scad-render skill, or python3 scripts/render-all.py\n"
        f"  3. Export + invariants: python3 scripts/export-all.py && "
        f"python3 scripts/check-invariants.py {stem}\n"
        f"  4. Param sweep (vendor libs first: bash scripts/vendor-libs.sh):\n"
        f"     npm run test:sweep -- tests/sweep/{stem}.test.ts\n"
        f"  5. Write the real catalog blurb + invariants claims (no TODOs left)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
