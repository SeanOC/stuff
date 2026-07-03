"""Invariants for the hex-profile LCD-pad stylus.

Built-ins (watertight, orphan fragments, PRINT_ANCHOR_BBOX drift) cover the
structural claims. The extras guard what this variant exists for: a single
connected body (the breakaway fin must hang off its ribs, not float), a tip
that still tapers to a dome and stays off the bed, a fillet that leaves a
real hexagon, and the lay-flat print story — the native orientation must
put a long flat contact patch on z=0, including the sacrificial fin's
footprint under the tip zone.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params, expect_connected_solids

# Vertices this close to z=0 count as bed contact.
_CONTACT_EPS_MM = 0.05


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    failures.extend(expect_connected_solids(ctx, 1))

    w = p.get("hex_width", 8)
    rt = p.get("tip_radius", 2)
    fr = p.get("edge_fillet", 1)
    length = p.get("total_length", 90)
    taper = p.get("taper_length", 14)

    # The tip must be narrower than the body's half-width, or it neither
    # tapers to a dome nor clears the bed when the stylus lies flat.
    if rt >= w / 2:
        failures.append(Failure(
            "tip",
            f"tip_radius={rt}mm >= half hex width {w / 2}mm; "
            f"tip won't taper and drags on the bed when lying flat",
        ))

    # The fillet must leave a real hexagon between the corner spheres.
    if fr >= w / 2:
        failures.append(Failure(
            "fillet",
            f"edge_fillet={fr}mm >= apothem budget {w / 2}mm; "
            f"corner spheres swallow the whole cross-section",
        ))

    # Lay-flat claim: the exported STL's native orientation must rest on a
    # hex flat — a bed-contact patch that runs most of the body length and
    # has real width (a line contact would mean the model is on an edge).
    verts = ctx["stl"].vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "layflat",
            "no vertices on z=0; model is not in its lay-flat print orientation",
        ))
        return failures

    span_x = contact[:, 0].max() - contact[:, 0].min()
    body_flat = length - taper
    if span_x < 0.6 * body_flat:
        failures.append(Failure(
            "layflat",
            f"bed contact spans {span_x:.1f}mm in X, expected >= "
            f"{0.6 * body_flat:.1f}mm (60% of the untapered body)",
        ))
    width_y = contact[:, 1].max() - contact[:, 1].min()
    if width_y < 1.5:
        failures.append(Failure(
            "layflat",
            f"bed contact is only {width_y:.2f}mm wide in Y; that's an "
            f"edge, not a hex flat — model would tip over",
        ))

    # Breakaway support claim: with include_support on, the fin must put
    # bed contact under the floating tip zone (past the taper start).
    if p.get("include_support", True) and contact[:, 0].max() < body_flat + 2:
        failures.append(Failure(
            "support",
            f"no bed contact past x={body_flat + 2:.1f}mm; the breakaway "
            f"fin under the tip zone is missing",
        ))

    return failures
