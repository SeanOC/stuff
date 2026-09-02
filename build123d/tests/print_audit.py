"""Deterministic printability audit for build123d holders (bead pst-jfyb).

Companion to the mount contracts (tests/mount_contracts.py): where those
assert a mount's *function*, this asserts a part's *printability* on the
target machine — a **Bambu Lab H2S, 0.4 mm nozzle, PLA/PCTG, no supports** —
turning the design-guidelines §1 rules into a standing, deterministic check
instead of a reviewer eyeball. See docs/design-guidelines.md §1 and §6.

What it checks (all against the model's declared PRINT ORIENTATION)
-------------------------------------------------------------------
Given a ``Part`` and a print-orientation unit vector ``up`` (the model-frame
direction that points AWAY from the build plate when printed), ``audit``
reports and flags:

* **max overhang** — the steepest downward-facing surface, measured as the
  angle from vertical (a vertical wall is 0°, a flat ceiling is 90°). Faces
  inside a registered library cutter's envelope are excluded (the slot
  profile is spec, not our overhang). Threshold **45°**.
* **longest bridge** — the widest *unsupported* span of any downward-facing
  near-horizontal planar face (a flat ceiling over a void). Measured by a
  conservative sampled local-span method: the face plane is rasterised, each
  cell kept only where the solid is above and a void is directly below (an
  actual unsupported ceiling point — not the mere bounding box), and the span
  is the largest *local width* over those cells (the shortest through-run in
  four in-plane directions, so a bridge is scored the short way it is printed).
  This does not read a thin annular or arc ledge — whose bbox is the full
  diameter but whose material is a narrow sliver — as a wide bridge.
  Threshold **10 mm**.
* **min wall** — the thinnest wall, sampled by marching inward along the
  surface normal from a grid of points on every face (a normal-direction
  ray-cast proxy: no ray engine is available, but point-membership is).
  Capped at ``WALL_CAP`` mm — only thin walls matter. Threshold **0.9 mm**
  whole-part (load-bearing 1.6 mm is deferred until faces can be tagged;
  see the bead note).
* **downward fillets** — any downward-facing *curved* face (a fillet on the
  bottom side prints as a rough curl; the guideline wants a 45° chamfer
  there instead). Any such face → fail. Library cutters excluded.
* **bed chamfer** — whether the plate-contact (bed-facing) edges carry a
  small 45° chamfer (elephant-foot relief). Advisory **warn**, never a fail.

Orientation convention
----------------------
``up`` is the unit vector, IN THE MODEL'S OWN COORDINATE FRAME, that points
up (away from the bed) in the declared print pose. The default ``(0, 0, 1)``
means "printed as modelled, +Z up". A model that prints on a different face
declares the axis that ends up pointing up — a holder printed back-plate-down
on its −Y face would declare ``(0, 1, 0)``. Models carry this as
``ModelSpec.print_orientation`` (default +Z; a production model declares a
non-default value only once it passes the audit at that orientation).

The numbers are computed on the build123d BRep (exact face normals and
geometry types), not on a tessellated mesh, so a fillet reads as one curved
face and an overhang angle is exact rather than triangle-quantised.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from build123d.topology import Part

# --- thresholds (design-guidelines.md §1) ---------------------------------
MAX_OVERHANG_DEG = 45.0   # steepest downward face from vertical
MAX_BRIDGE_MM = 10.0      # longest unsupported flat span
MIN_WALL_MM = 0.9         # thinnest wall (whole-part floor; load-bearing 1.6 deferred)
BED_CHAMFER_MIN_MM = 0.3  # elephant-foot chamfer window (warn only)
BED_CHAMFER_MAX_MM = 0.5

# --- probe constants ------------------------------------------------------
WALL_CAP = 3.0            # mm: wall marching stops here (only thin walls matter)
_DOWN_EPS = 0.02          # a face is "downward" when normal·up < −this
_BED_EPS = 1e-4           # mm: a face is bed-contact when its whole extent sits here
_FLAT_COS = 0.985         # near-horizontal ceiling: normal·up ≤ −this (≈ within 10°)
_CUTTER_MARGIN = 0.6      # mm: library-cutter bbox is grown this much before excluding
_NORMAL_PROBE = 0.05      # mm: offset used to orient a face normal outward
_OVERHANG_UV = (0.1, 0.3, 0.5, 0.7, 0.9)  # face UV grid for overhang / curved-face scan
_WALL_UV = (0.3, 0.5, 0.7)                # sparser grid for the (costlier) wall march
_CHAMFER_MAX_EXTENT = 1.0  # mm: a bed chamfer's rise along `up` is at most this
_CHAMFER_ANGLE_LO = 25.0   # deg: a 45° bed chamfer reads in this band ...
_CHAMFER_ANGLE_HI = 65.0   # ... allowing for fillet-fallback slopes
_BRIDGE_STEP = 0.5         # mm: finest raster cell for the bridge local-span scan
_BRIDGE_MAX_SAMPLES = 80   # cap cells per axis (coarsen the step on a large face)
_BRIDGE_PROBE = 0.1        # mm: offset used to test solid-above / void-below a cell


@dataclass(frozen=True)
class DownwardFillet:
    """One downward-facing curved face (a bottom-side fillet) — a printability
    failure (use a 45° chamfer there instead)."""

    geom_type: str
    location: tuple[float, float, float]
    overhang_deg: float


@dataclass(frozen=True)
class PrintAuditReport:
    """The typed audit result (AC 1). ``ok`` is False when any blocking rule
    trips; the bed-chamfer status is advisory and never blocks."""

    model: str
    orientation: tuple[float, float, float]
    max_overhang_deg: float
    longest_bridge_mm: float
    min_wall_mm: float
    downward_fillets: tuple[DownwardFillet, ...]
    bed_chamfer: str  # "present" | "absent" | "n/a"
    # thresholds echoed so a report is self-describing when pasted into a PR
    overhang_threshold_deg: float = MAX_OVERHANG_DEG
    bridge_threshold_mm: float = MAX_BRIDGE_MM
    wall_threshold_mm: float = MIN_WALL_MM

    def failures(self) -> list[str]:
        """Blocking rule violations (empty = printable). Bed chamfer excluded
        — it is a warn."""
        out: list[str] = []
        if self.max_overhang_deg > self.overhang_threshold_deg + 1e-6:
            out.append(
                f"overhang {self.max_overhang_deg:.1f}° > "
                f"{self.overhang_threshold_deg:.0f}° (steeper than 45° from vertical)"
            )
        if self.longest_bridge_mm > self.bridge_threshold_mm + 1e-6:
            out.append(
                f"bridge {self.longest_bridge_mm:.1f} mm > "
                f"{self.bridge_threshold_mm:.0f} mm unsupported span"
            )
        if self.min_wall_mm < self.wall_threshold_mm - 1e-6:
            out.append(
                f"wall {self.min_wall_mm:.2f} mm < {self.wall_threshold_mm:.1f} mm minimum"
            )
        if self.downward_fillets:
            locs = ", ".join(
                f"{d.geom_type}@({d.location[0]:.0f},{d.location[1]:.0f},"
                f"{d.location[2]:.0f})"
                for d in self.downward_fillets
            )
            out.append(
                f"{len(self.downward_fillets)} downward-facing curved face(s) "
                f"[{locs}] — use a 45° chamfer, not a bottom fillet"
            )
        return out

    @property
    def ok(self) -> bool:
        return not self.failures()

    def format(self) -> str:
        """A compact, PR-pasteable report (design-guidelines §6 items 1–3)."""
        ox, oy, oz = self.orientation
        lines = [
            f"print audit: {self.model}  (up = ({ox:.2f}, {oy:.2f}, {oz:.2f}))",
            f"  overhang   : {self.max_overhang_deg:5.1f}°   "
            f"(≤ {self.overhang_threshold_deg:.0f}°) "
            f"{'OK' if self.max_overhang_deg <= self.overhang_threshold_deg + 1e-6 else 'FAIL'}",
            f"  bridge     : {self.longest_bridge_mm:5.1f} mm (≤ {self.bridge_threshold_mm:.0f} mm) "
            f"{'OK' if self.longest_bridge_mm <= self.bridge_threshold_mm + 1e-6 else 'FAIL'}",
            f"  min wall   : {self.min_wall_mm:5.2f} mm (≥ {self.wall_threshold_mm:.1f} mm) "
            f"{'OK' if self.min_wall_mm >= self.wall_threshold_mm - 1e-6 else 'FAIL'}"
            + (f" [capped at {WALL_CAP:.0f} mm]" if self.min_wall_mm >= WALL_CAP - 1e-6 else ""),
            f"  dn fillets : {len(self.downward_fillets):5d}     (= 0)    "
            f"{'OK' if not self.downward_fillets else 'FAIL'}",
            f"  bed chamfer: {self.bed_chamfer:>7}   (warn)",
            f"  => {'PASS' if self.ok else 'FAIL: ' + '; '.join(self.failures())}",
        ]
        return "\n".join(lines)


# --- geometry helpers -----------------------------------------------------

def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    m = math.sqrt(sum(c * c for c in v))
    if m == 0.0:
        raise ValueError("print orientation must be a non-zero vector")
    return (v[0] / m, v[1] / m, v[2] / m)


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _height(p, up) -> float:
    """Signed distance along ``up`` — the print-space Z of a model-space point."""
    return p.X * up[0] + p.Y * up[1] + p.Z * up[2]


def _in_plane_axes(up):
    """Two orthonormal axes spanning the build-plate plane (⊥ up)."""
    seed = (1.0, 0.0, 0.0) if abs(up[0]) < 0.9 else (0.0, 1.0, 0.0)
    u1 = _unit(tuple(seed[i] - _dot(seed, up) * up[i] for i in range(3)))
    u2 = (
        up[1] * u1[2] - up[2] * u1[1],
        up[2] * u1[0] - up[0] * u1[2],
        up[0] * u1[1] - up[1] * u1[0],
    )
    return u1, u2


def _cutter_boxes(cutters, margin=_CUTTER_MARGIN):
    """Axis-aligned bounding boxes of the library cutters, grown by ``margin``
    so faces the cutter carved are reliably inside (the slot profile is spec)."""
    boxes = []
    for cutter in cutters:
        bb = cutter.bounding_box()
        boxes.append(
            (
                bb.min.X - margin, bb.min.Y - margin, bb.min.Z - margin,
                bb.max.X + margin, bb.max.Y + margin, bb.max.Z + margin,
            )
        )
    return boxes


def _bbox_corners(bb):
    """The eight corners of a build123d ``BoundBox`` as (x, y, z) tuples."""
    xs = (bb.min.X, bb.max.X)
    ys = (bb.min.Y, bb.max.Y)
    zs = (bb.min.Z, bb.max.Z)
    return [(x, y, z) for x in xs for y in ys for z in zs]


def _in_any_box(x: float, y: float, z: float, boxes) -> bool:
    for (x0, y0, z0, x1, y1, z1) in boxes:
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1:
            return True
    return False


def _outward_normal(part: Part, face):
    """(center, outward-oriented unit normal) for a face of ``part``.

    ``normal_at`` follows the face's own orientation, which boolean ops can
    leave pointing inward; flip it using a point-membership test so it always
    points out of the solid."""
    c = face.center()
    n = face.normal_at(c)
    probe = (c.X + n.X * _NORMAL_PROBE, c.Y + n.Y * _NORMAL_PROBE, c.Z + n.Z * _NORMAL_PROBE)
    if part.is_inside(probe):
        n = -n
    return c, n


def _face_samples(face, uvs):
    """(point, normal) at a UV grid on ``face`` (skips points OCC can't map)."""
    out = []
    for u in uvs:
        for v in uvs:
            try:
                p = face.position_at(u, v)
                n = face.normal_at(p)
            except Exception:
                continue
            out.append((p, n))
    return out


def _signed(sample_n, ref_n):
    """Orient a per-sample normal to agree with the face's outward normal."""
    return sample_n if _dot(
        (sample_n.X, sample_n.Y, sample_n.Z), (ref_n.X, ref_n.Y, ref_n.Z)
    ) >= 0 else -sample_n


# --- individual checks ----------------------------------------------------

def _max_overhang(part, up, boxes, hmin):
    """Steepest downward-facing surface, degrees from vertical (0 = vertical
    wall, 90 = flat ceiling). Bed-contact faces and library-cutter faces are
    excluded."""
    worst = 0.0
    for face in part.faces():
        c, n = _outward_normal(part, face)
        if _in_any_box(c.X, c.Y, c.Z, boxes):
            continue
        verts = [v for v in face.vertices()]
        if verts and max(_height(v, up) for v in verts) <= hmin + _BED_EPS:
            continue  # sits in the bed plane — supported by the plate
        for p, sn in _face_samples(face, _OVERHANG_UV) or [(c, n)]:
            if _in_any_box(p.X, p.Y, p.Z, boxes):
                continue
            s = _signed(sn, n)
            cdot = s.X * up[0] + s.Y * up[1] + s.Z * up[2]
            if cdot < -_DOWN_EPS:
                worst = max(worst, math.degrees(math.asin(min(1.0, -cdot))))
    return worst


def _downward_curved_faces(part, up, boxes, hmin):
    """Downward-facing NON-planar faces — bottom-side fillets that print as a
    rough curl (guideline: use a 45° chamfer there). Library cutters excluded."""
    found: list[DownwardFillet] = []
    for face in part.faces():
        if str(face.geom_type) == "GeomType.PLANE":
            continue
        c, n = _outward_normal(part, face)
        if _in_any_box(c.X, c.Y, c.Z, boxes):
            continue
        verts = [v for v in face.vertices()]
        if verts and max(_height(v, up) for v in verts) <= hmin + _BED_EPS:
            continue
        worst = 0.0
        downward = False
        for p, sn in _face_samples(face, _OVERHANG_UV) or [(c, n)]:
            if _in_any_box(p.X, p.Y, p.Z, boxes):
                continue
            s = _signed(sn, n)
            cdot = s.X * up[0] + s.Y * up[1] + s.Z * up[2]
            if cdot < -_DOWN_EPS:
                downward = True
                worst = max(worst, math.degrees(math.asin(min(1.0, -cdot))))
        if downward:
            found.append(
                DownwardFillet(
                    geom_type=str(face.geom_type).replace("GeomType.", ""),
                    location=(round(c.X, 2), round(c.Y, 2), round(c.Z, 2)),
                    overhang_deg=round(worst, 1),
                )
            )
    return tuple(found)


def _max_local_span(grid, step) -> float:
    """Largest local width over the marked cells of a boolean ``grid``.

    For every marked cell, take the contiguous marked run THROUGH it in each of
    four in-plane directions (rows, columns, both diagonals) and keep the
    SHORTEST — a bridge is printed across its narrow way, so its local width is
    its shortest through-run. The face's span is the largest such width. A thin
    sliver (annular ledge) is narrow in some direction everywhere, so it never
    reads as a wide bridge, whatever its bounding box."""
    nx = len(grid)
    ny = len(grid[0]) if nx else 0
    if nx == 0 or ny == 0:
        return 0.0
    inf = float("inf")
    minlen = [[inf] * ny for _ in range(nx)]

    def _apply(cells, unit_len):
        # ``cells`` are ordered along one line; score each maximal marked run.
        k, m = 0, len(cells)
        while k < m:
            if not grid[cells[k][0]][cells[k][1]]:
                k += 1
                continue
            start = k
            while k < m and grid[cells[k][0]][cells[k][1]]:
                k += 1
            seg = (k - start) * unit_len
            for t in range(start, k):
                i, j = cells[t]
                if seg < minlen[i][j]:
                    minlen[i][j] = seg

    diag = step * math.sqrt(2.0)
    for j in range(ny):                       # rows  (1, 0)
        _apply([(i, j) for i in range(nx)], step)
    for i in range(nx):                       # cols  (0, 1)
        _apply([(i, j) for j in range(ny)], step)
    d1: dict = {}
    d2: dict = {}
    for i in range(nx):
        for j in range(ny):
            d1.setdefault(i - j, []).append((i, j))   # diagonal   (1, 1)
            d2.setdefault(i + j, []).append((i, j))   # anti-diag  (1, -1)
    for cells in d1.values():
        _apply(sorted(cells), diag)
    for cells in d2.values():
        _apply(sorted(cells), diag)

    best = 0.0
    for i in range(nx):
        for j in range(ny):
            if grid[i][j] and minlen[i][j] < inf:
                best = max(best, minlen[i][j])
    return best


def _longest_bridge(part, up, boxes, hmin):
    """Widest unsupported flat span, measured (not bounding-boxed). For each
    downward-facing near-horizontal planar face above the bed, rasterise the
    face plane, keep only cells that are an actual unsupported ceiling (solid
    just above, void just below), and take the largest local width over them
    (see ``_max_local_span``)."""
    u1, u2 = _in_plane_axes(up)
    eps = _BRIDGE_PROBE
    worst = 0.0
    for face in part.faces():
        if str(face.geom_type) != "GeomType.PLANE":
            continue
        c, n = _outward_normal(part, face)
        if _in_any_box(c.X, c.Y, c.Z, boxes):
            continue
        cdot = n.X * up[0] + n.Y * up[1] + n.Z * up[2]
        if cdot > -_FLAT_COS:  # not a near-horizontal ceiling
            continue
        # In-plane extent + top height from the face's bbox corners — robust to
        # a full-circle face (no vertices), unlike sampling face.vertices().
        corners = _bbox_corners(face.bounding_box())
        if max(_dot(p, up) for p in corners) <= hmin + _BED_EPS:
            continue  # sits in the bed plane — supported by the plate
        e1 = [_dot(p, u1) for p in corners]
        e2 = [_dot(p, u2) for p in corners]
        a0, a1, b0, b1 = min(e1), max(e1), min(e2), max(e2)
        ext = max(a1 - a0, b1 - b0)
        if ext <= 0:
            continue
        # Exact plane height at each in-plane cell: solve n·(a·u1+b·u2+t·up)=n·c
        # so a face tilted up to ~10° is probed on its own surface, not a flat h.
        nn = (n.X, n.Y, n.Z)
        ndu1, ndu2, ndup = _dot(nn, u1), _dot(nn, u2), _dot(nn, up)
        ndc = nn[0] * c.X + nn[1] * c.Y + nn[2] * c.Z
        step = max(_BRIDGE_STEP, ext / _BRIDGE_MAX_SAMPLES)
        nx = max(1, int(math.ceil((a1 - a0) / step)))
        ny = max(1, int(math.ceil((b1 - b0) / step)))
        grid = [[False] * ny for _ in range(nx)]
        for i in range(nx):
            ai = a0 + (i + 0.5) * step
            for j in range(ny):
                bj = b0 + (j + 0.5) * step
                t = (ndc - ai * ndu1 - bj * ndu2) / ndup
                qx = ai * u1[0] + bj * u2[0] + t * up[0]
                qy = ai * u1[1] + bj * u2[1] + t * up[1]
                qz = ai * u1[2] + bj * u2[2] + t * up[2]
                if _in_any_box(qx, qy, qz, boxes):
                    continue
                above = (qx + up[0] * eps, qy + up[1] * eps, qz + up[2] * eps)
                below = (qx - up[0] * eps, qy - up[1] * eps, qz - up[2] * eps)
                if part.is_inside(above) and not part.is_inside(below):
                    grid[i][j] = True
        worst = max(worst, _max_local_span(grid, step))
    return worst


def _min_wall(part, up, boxes):
    """Thinnest wall, sampled by marching inward along the outward normal from
    a UV grid on every face until the ray exits the solid (a normal-direction
    ray-cast proxy). Capped at ``WALL_CAP`` — only thin walls matter."""
    best = WALL_CAP
    for face in part.faces():
        c, n = _outward_normal(part, face)
        for p, sn in _face_samples(face, _WALL_UV):
            if _in_any_box(p.X, p.Y, p.Z, boxes):
                continue
            s = _signed(sn, n)

            def inside(depth: float) -> bool:
                return part.is_inside(
                    (p.X - s.X * depth, p.Y - s.Y * depth, p.Z - s.Z * depth)
                )

            if not inside(0.02):      # sample sits over a void (e.g. a pocket)
                continue
            if inside(best):          # already thicker than the running minimum
                continue
            lo, hi = 0.02, best
            for _ in range(18):       # bisect the exit depth
                mid = (lo + hi) / 2.0
                if inside(mid):
                    lo = mid
                else:
                    hi = mid
            best = min(best, lo)
    return best


def _bed_chamfer(part, up, hmin) -> str:
    """Advisory: is there a small 45° chamfer on the plate-contact edges?

    "present" when a planar downward face at ~45° touches the bed and rises
    only a chamfer's worth along ``up``; "absent" when a bed-contact face
    exists but no such chamfer does; "n/a" when the part has no bed-contact
    face at all."""
    has_bed = False
    has_chamfer = False
    for face in part.faces():
        if str(face.geom_type) != "GeomType.PLANE":
            continue
        c, n = _outward_normal(part, face)
        cdot = n.X * up[0] + n.Y * up[1] + n.Z * up[2]
        if cdot >= -_DOWN_EPS:
            continue
        verts = [v for v in face.vertices()]
        if not verts:
            continue
        heights = [_height(v, up) for v in verts]
        if max(heights) <= hmin + _BED_EPS:
            has_bed = True
            continue
        angle = math.degrees(math.asin(min(1.0, -cdot)))
        extent = max(heights) - min(heights)
        if (
            _CHAMFER_ANGLE_LO <= angle <= _CHAMFER_ANGLE_HI
            and min(heights) <= hmin + _BED_EPS
            and extent <= _CHAMFER_MAX_EXTENT
        ):
            has_chamfer = True
    if has_chamfer:
        return "present"
    return "absent" if has_bed else "n/a"


def audit(
    part: Part,
    orientation: tuple[float, float, float] = (0.0, 0.0, 1.0),
    *,
    cutters=(),
    model: str = "part",
) -> PrintAuditReport:
    """Run the full printability audit (AC 1).

    Args:
        part: the built model.
        orientation: the print-orientation unit vector — the model-frame
            direction that points UP (away from the bed). Default +Z.
        cutters: registered library cutter solids whose envelopes are excluded
            from the overhang / bridge / fillet checks (the slot profile is
            spec). Typically a model's ``mount_fixtures(...).cutters``.
        model: a label for the report.
    """
    up = _unit(orientation)
    boxes = _cutter_boxes(list(cutters))
    verts = [v for v in part.vertices()]
    if not verts:
        raise ValueError(f"{model}: part has no geometry to audit")
    hmin = min(_height(v, up) for v in verts)

    return PrintAuditReport(
        model=model,
        orientation=tuple(round(o, 6) for o in up),
        max_overhang_deg=round(_max_overhang(part, up, boxes, hmin), 1),
        longest_bridge_mm=round(_longest_bridge(part, up, boxes, hmin), 2),
        min_wall_mm=round(_min_wall(part, up, boxes), 3),
        downward_fillets=_downward_curved_faces(part, up, boxes, hmin),
        bed_chamfer=_bed_chamfer(part, up, hmin),
    )
