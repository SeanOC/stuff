"""Invariants for the Ryobi P2860 strap saddle (pst-ege).

A crowned prong projecting from a 2x3 openGrid plate; the sprayer's
padded shoulder strap loops over it like a shoulder. Printed as a
mirrored pair (side=right|left @param, filename-expanded exports).
Numbered claims:

  1. **Single connected solid.** Snaps, plate, root flare, and prong
     weld into one body.

  2. **Bed contact spans exactly the 2x3 snap grid** on the 28mm pitch
     (52.8 x 80.8mm): proves the snaps-down print orientation and pins
     snap count and pitch. Identical for both mirror variants.

  3. **Directional snaps point their strong nub +Y (usage-up,
     operator-stated in pst-ege).** Vertex-based per the pst-ozs rework
     (PR #15): in the snap-only z band the only geometry reaching past
     the 24.8mm core is the nubs — strong front nub tips out 13.2mm
     from a snap center, rear click nub 12.8mm — so the +Y edge of the
     top row must reach 13.2 and the -Y edge of the bottom row must
     stop at 12.8. NOT contains()/raycast (known CI parity flakiness).
     Runs on BOTH side variants: also catches a refactor that
     accidentally pulls the snaps inside the side mirror.

  4. **Saddle dip + retention lip.** The lip zone (last 12mm of the
     prong) crests lip_height above the dip trough, tracking the
     model's clamp when lip_height/strap_channel demand a chord wider
     than the channel. Vertex extents in z slabs; the trough slab is
     centered on the dip cylinder's lowest line recomputed from params.

  5. **Mirror chirality.** The crown apex (highest crest vertices) sits
     ~+6mm outboard: x > +2 for side=right, x < -2 for side=left. Pins
     that the side param actually mirrors the body — and, paired with
     claim 3, that it mirrors ONLY the body.
"""

from __future__ import annotations

import math

from scripts.invariants import Failure, as_default_params, expect_connected_solids

_CONTACT_EPS_MM = 0.05
_SNAP_PITCH = 28.0
_SNAP_W = 24.8

_COLS = 2
_ROWS = 3
_ROW_TOP_Y = 28.0     # snap row centers at y = -28, 0, +28
_ROW_BOT_Y = -28.0
_PLATE_T = 6.0
_PRONG_TOP = 15.0     # crown apex height (profile centered on plate)
_LIP_T = 12.0
_APEX_OFF = 6.0


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])
    mesh = ctx["stl"]

    side = str(p.get("side", "right"))
    snap_lite = bool(p.get("snap_lite", False))
    strap_channel = float(p.get("strap_channel", 80))
    saddle_radius = float(p.get("saddle_radius", 55))
    lip_height = float(p.get("lip_height", 12))

    snap_h = 3.4 if snap_lite else 6.8
    plate_z0 = snap_h - 0.02
    plate_zf = plate_z0 + _PLATE_T
    z_lip = plate_zf + strap_channel

    failures.extend(expect_connected_solids(ctx, 1))

    verts = mesh.vertices
    contact = verts[verts[:, 2] < _CONTACT_EPS_MM]
    if len(contact) == 0:
        failures.append(Failure(
            "orientation",
            "no vertices on z=0; model is not in its snaps-down print "
            "orientation",
        ))
        return failures

    # 2. Bed contact = 2x3 snap grid.
    span_x = contact[:, 0].max() - contact[:, 0].min()
    span_y = contact[:, 1].max() - contact[:, 1].min()
    want_x = (_COLS - 1) * _SNAP_PITCH + _SNAP_W
    want_y = (_ROWS - 1) * _SNAP_PITCH + _SNAP_W
    if abs(span_x - want_x) > 0.5 or abs(span_y - want_y) > 0.5:
        failures.append(Failure(
            "snapgrid",
            f"bed contact spans {span_x:.1f} x {span_y:.1f}mm but the "
            f"{_COLS}x{_ROWS} snap grid on the 28mm pitch should span "
            f"{want_x:.1f} x {want_y:.1f}mm — snap count or pitch drifted",
        ))

    # 3. Snap orientation, vertex-based (pst-ozs convention).
    band = verts[(verts[:, 2] > 0.05) & (verts[:, 2] < plate_z0 - 0.05)]
    if len(band) == 0:
        failures.append(Failure(
            "snap-load-orientation",
            "no vertices in the snap-only z band below the plate — "
            "snaps missing",
        ))
    else:
        up_reach = float(band[:, 1].max()) - _ROW_TOP_Y     # +Y side
        down_reach = _ROW_BOT_Y - float(band[:, 1].min())   # -Y side
        if abs(up_reach - 13.2) > 0.15 or abs(down_reach - 12.8) > 0.15:
            failures.append(Failure(
                "snap-load-orientation",
                f"directional snap front nub not pointing +Y (usage-up): "
                f"+Y reach {up_reach:.2f}mm from the top snap row (want "
                f"13.2, the strong nub) and -Y reach {down_reach:.2f}mm "
                f"from the bottom row (want 12.8, the click nub); the "
                f"strong hook must take the lever-out load",
            ))

    # 4. Dip trough vs lip crest, mirroring the model's clamp math.
    hc_raw = math.sqrt(max(0.0, 2 * saddle_radius * lip_height - lip_height ** 2))
    hc = min(hc_raw, (strap_channel - 1.5) / 2)
    rise = saddle_radius - math.sqrt(saddle_radius ** 2 - hc ** 2)
    trough_cz = z_lip - hc
    crest = verts[verts[:, 2] > z_lip + 2.0]
    trough = verts[abs(verts[:, 2] - trough_cz) < 3.0]
    if len(crest) == 0 or len(trough) == 0:
        failures.append(Failure(
            "saddle-lip",
            f"no vertices in the lip zone (z>{z_lip + 2:.1f}) or trough "
            f"slab (z~{trough_cz:.1f}) — prong length or dip position "
            "drifted",
        ))
    else:
        crest_y = float(crest[:, 1].max())
        trough_y = float(trough[:, 1].max())
        got_rise = crest_y - trough_y
        if abs(crest_y - _PRONG_TOP) > 0.5 or abs(got_rise - rise) > 0.6:
            failures.append(Failure(
                "saddle-lip",
                f"lip crest at y={crest_y:.2f} (want {_PRONG_TOP}), rise "
                f"above trough {got_rise:.2f}mm (want {rise:.2f} for "
                f"lip_height={lip_height:g}, saddle_radius="
                f"{saddle_radius:g}) — the strap retention lip drifted",
            ))

    # 5. Crown apex chirality matches the side param.
    if len(crest) > 0:
        apex = crest[crest[:, 1] > crest[:, 1].max() - 0.5]
        apex_mid = float((apex[:, 0].min() + apex[:, 0].max()) / 2)
        want_sign = 1.0 if side == "right" else -1.0
        if apex_mid * want_sign < 2.0:
            failures.append(Failure(
                "mirror-chirality",
                f"crown apex midline at x={apex_mid:.2f} but side="
                f"{side} wants it {'>+2' if want_sign > 0 else '<-2'} "
                f"(apex offset {_APEX_OFF}mm outboard) — the side param "
                "is not mirroring the body",
            ))

    return failures
