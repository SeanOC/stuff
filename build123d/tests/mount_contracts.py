"""Deterministic geometry contracts for known mount types (bead pst-3eun).

Motivation
----------
The v2 Multiconnect slot shipped upside-down and sealed — a pocket with no
way in — yet it passed watertight export, codex review, and the render audit
(a sealed pocket is watertight too, and reads fine at a glance). Watertight
and volume checks cannot see a *missing aperture* or a *flipped opening*.
These contracts can: they are boolean-geometry assertions about a mount's
FUNCTION, built entirely from the opengrid library's own parts as fixtures.

How it wires in
---------------
A model declares the mount types it carries via ``ModelSpec.mounts`` (e.g.
``mounts=("multiconnect-slot",)``) and exposes a ``mount_fixtures(mount_type,
values)`` hook in its module returning a ``registry.MountFixtures`` (100%
library geometry in the model's own frame). tests/test_mount_contracts.py
auto-parametrizes ``verify(mount_type, part, fx)`` over every registered
model tagged with a mount — like the export/watertight suite, a new model
inherits the whole contract for free.

The multiconnect-slot contract asserts six things:
  (a) APERTURE     — the slot void breaks through the plate's BOTTOM face, so
                     a wall head can actually enter (the v2 sealed-pocket bug).
  (b) ORIENTATION  — the channel opening faces -Z (bottom), never the top
                     (the v2 upside-down bug).
  (c) SEAT CLEARANCE — a library RoundHead at the seated pose fits the carved
                     pocket with clearance (empty intersection with the model).
  (d) ENTRY TRAVEL — that RoundHead swept from below the plate up to the seat
                     never collides with the model (a continuous insertion
                     path exists, not merely a reachable seat).
  (e) RETENTION    — a seated RoundHead pulled straight off the wall (along the
                     mount face normal) FOULS the plate: the narrow lip holds
                     the head's wide flange (the v3 print bug — the pocket was
                     carved inverted, so the head pulled straight off and (a)-(d)
                     all passed since none is sensitive to the depth profile).
  (f) PROFILE      — the slot void is NARROW at the open (mount) face and WIDE
                     inside, the dovetail lip (e) relies on (inverted on v3).

Adding a new mount contract
---------------------------
1. Add the mount name to ``registry.KNOWN_MOUNTS``.
2. Write ``def verify_<mount>(part, fx): ...`` here (raise AssertionError on
   violation) and register it in ``CONTRACTS``. The import-time coverage
   assertion below fails loudly if a known mount has no contract.
3. Add its advisory rubric to ``scripts/render_review.py::RUBRICS``
   (tests/test_render_review.py requires one per known mount).
4. In each model that carries it, tag ``mounts=(...)`` and implement the
   ``mount_fixtures`` hook.
"""
from __future__ import annotations

import math
from collections.abc import Callable

from build123d import Align, Axis, Box, Plane, Pos, Rot, Solid, section
from build123d.topology import Part
from opengrid.multiconnect import RoundHead

from holders.registry import KNOWN_MOUNTS, ModelSpec, MountFixtures

# Compatibility name for existing contract callers.
from holders.registry import resolve_mount_fixtures as resolve_fixtures

# Boolean intersections around coincident faces are noisy; every check uses an
# explicit tolerance, never an exact-zero comparison (plan-review guidance).
_EMPTY_VOL = 1.0      # mm^3: a residual at/under this reads as "essentially empty"
_SOLID_MIN = 0.5      # mm^3: occupied volume proving a small probe sits in solid
_APERTURE_MIN = 10.0  # mm^3: cutter material the slot must remove at the bottom face
_TRAVEL_TOL = 2.0     # mm^3: entry-travel grazing tolerance (intended snap-notch contact)
_SLAB = 1.0           # mm: thickness of the face-probe slabs
_RETENTION_MIN = 1.0  # mm^3: a seated head pulled off the wall must foul the plate
                      #        by at least this — the lip retains the head's flange
_PROFILE_MIN_DELTA = 3.0  # mm: min (deep width - surface width) proving the dovetail
                          #     is narrow at the open face and wide inside (retention)
_PULL_DISTS = (0.5, 1.0, 2.0)  # mm: off-wall pull distances the head must be held at
_SURFACE_IN = 0.4     # mm: depth just inside the mount face for the surface width probe
_DEEP_IN = 3.75       # mm: depth near the pocket back for the deep width probe
_FLANK_OFFSET = 1.5   # mm: how far beyond the slot's X-extent the plate must
                      #     still be solid (into the plate's own side margin)
_OC_END_STOP_MIN = 5.0  # mm^3: an openConnect head pushed 1 mm past its seat must
                        #     foul more than its whole lock nub (1.42 mm^3) could

_CENTER3 = (Align.CENTER, Align.CENTER, Align.CENTER)


def _residual_vol(part: Part, solid: Part) -> float:
    """Volume of ``part ∩ solid`` (0.0 when they do not overlap)."""
    inter = part.intersect(solid)
    if inter is None:
        return 0.0
    return sum(s.volume for s in inter.solids())


def _face_slab(part: Part, *, bottom: bool) -> Part:
    """A thin slab covering the whole min-Z (bottom) or max-Z (top) face."""
    bb = part.bounding_box()
    z = bb.min.Z + _SLAB / 2 if bottom else bb.max.Z - _SLAB / 2
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    sx = (bb.max.X - bb.min.X) + 10.0
    sy = (bb.max.Y - bb.min.Y) + 10.0
    return Pos(cx, cy, z) * Box(sx, sy, _SLAB, align=_CENTER3)


def _require_z_entry(fx: MountFixtures, mount: str = "multiconnect-slot") -> None:
    ax = tuple(round(a, 6) for a in fx.entry_axis)
    if ax != (0.0, 0.0, 1.0):
        raise AssertionError(
            f"{mount} contract currently assumes entry_axis=(0,0,1), "
            f"got {fx.entry_axis} — generalize the face/travel probes to extend it"
        )


def _require_y_face(fx: MountFixtures, mount: str = "multiconnect-slot") -> None:
    ax = tuple(round(a, 6) for a in fx.face_normal)
    if ax != (0.0, -1.0, 0.0):
        raise AssertionError(
            f"{mount} contract currently assumes face_normal=(0,-1,0), "
            f"got {fx.face_normal} — generalize the retention/profile probes to extend it"
        )


def _cutter_x_width(cutter: Part, y: float, z: float) -> float:
    """Width across X of a cutter (the slot void) in a thin Y*Z slab.

    With entry_axis=+Z and face_normal=-Y the dovetail taper runs along Y and
    the width that captures/releases the head runs along X, so this measures
    the pocket's clear span at a given depth (y) and the seat height (z)."""
    slab = Pos(0.0, y, z) * Box(1000.0, 0.2, 0.4, align=_CENTER3)
    inter = cutter.intersect(slab)
    solids = list(inter.solids()) if inter is not None else []
    if not solids:
        return 0.0
    xs = [v.X for s in solids for v in s.vertices()]
    return max(xs) - min(xs)


# --- multiconnect-slot assertions ----------------------------------------

def assert_aperture(part: Part, fx: MountFixtures) -> None:
    """(a) The slot void breaks THROUGH the plate's bottom face, and the plate
    stays solid flanking it. A sealed pocket removes nothing at the bottom and
    fails here — the exact failure class watertight tests cannot catch."""
    _require_z_entry(fx)
    bottom = _face_slab(part, bottom=True)
    removed = sum(_residual_vol(c, bottom) for c in fx.cutters)
    assert removed > _APERTURE_MIN, (
        f"no bottom aperture: the slot cutters remove only {removed:.2f} mm^3 "
        f"at the plate's bottom face (need > {_APERTURE_MIN}) — a sealed pocket "
        "has no way in"
    )
    bb = part.bounding_box()
    y_in = bb.min.Y + 2.0          # just inside the -Y mount face
    z_low = bb.min.Z + 0.5         # straddling the bottom edge
    for loc in fx.seat_locs:
        x = loc.position.X
        channel = Pos(x, y_in, z_low) * Box(4.0, 3.0, _SLAB, align=_CENTER3)
        r = _residual_vol(part, channel)
        assert r < _EMPTY_VOL, (
            f"slot at x={x:.1f} is sealed at the bottom edge (residual {r:.2f} "
            "mm^3) — no aperture for the wall head"
        )
    # Not merely "the whole bottom is missing": the plate is solid just BESIDE
    # the slot. Anchor the flank probe to the slot's own X-extent, not the
    # part's global max-X: the plate is sized to the slot envelope + margin and
    # is now typically NARROWER than the cup (design-guidelines §3), so
    # bb.max.X is the collar edge, with no plate behind the mount face there.
    slot_max_x = max(c.bounding_box().max.X for c in fx.cutters)
    flank_x = slot_max_x + _FLANK_OFFSET   # into the plate's side margin
    flank = Pos(flank_x, y_in, z_low) * Box(1.0, 3.0, _SLAB, align=_CENTER3)
    fr = _residual_vol(part, flank)
    assert fr > _SOLID_MIN, (
        f"plate not solid flanking the slot aperture (edge residual {fr:.2f} mm^3)"
    )


def assert_orientation(part: Part, fx: MountFixtures) -> None:
    """(b) The channel opening faces -Z: the cutters break the BOTTOM face but
    not the TOP, and the plate is solid above each seat (the inverse of the v2
    top-opening bug)."""
    _require_z_entry(fx)
    top = _face_slab(part, bottom=False)
    at_top = sum(_residual_vol(c, top) for c in fx.cutters)
    assert at_top < _EMPTY_VOL, (
        f"slot opens at the TOP face ({at_top:.2f} mm^3 removed there) — the "
        "opening must face -Z (bottom) so the holder lowers onto the wall head"
    )
    bb = part.bounding_box()
    y_in = bb.min.Y + 2.0
    # Probe just above each slot's own closed (top) end, not the part's global
    # max-Z: the plate is sized to the slot envelope and may be SHORTER than
    # the cup (design-guidelines §3), so bb.max.Z can be the collar top, well
    # above the plate. The slot cap is what must be solid — the head must not
    # exit upward — so anchor the probe to the cutter's top.
    for cutter, loc in zip(fx.cutters, fx.seat_locs):
        x = loc.position.X
        slot_top = cutter.bounding_box().max.Z
        above = Pos(x, y_in, slot_top + _SLAB) * Box(4.0, 3.0, _SLAB, align=_CENTER3)
        r = _residual_vol(part, above)
        assert r > _SOLID_MIN, (
            f"plate not solid just above the slot at x={x:.1f} (residual "
            f"{r:.2f} mm^3) — the channel appears to run out the TOP"
        )


def assert_seat_clearance(part: Part, fx: MountFixtures) -> None:
    """(c) A library RoundHead at each seated pose fits the carved pocket with
    clearance — the pocket genuinely receives the head (empty intersection)."""
    for loc in fx.seat_locs:
        head = loc * RoundHead()
        assert head.volume > 100.0, "sanity: the library RoundHead is a real solid"
        r = _residual_vol(part, head)
        assert r < _EMPTY_VOL, (
            f"seated head fouls the model at x={loc.position.X:.1f} "
            f"(residual {r:.3f} mm^3) — the pocket does not clear the head"
        )


def assert_entry_travel(part: Part, fx: MountFixtures) -> None:
    """(d) A RoundHead swept along +Z from below the plate to the seat never
    collides with the model (beyond a small snap-notch grazing tolerance) —
    proving a continuous insertion path, not just a reachable seat."""
    _require_z_entry(fx)
    bb = part.bounding_box()
    for loc in fx.seat_locs:
        seated = loc * RoundHead()
        seat_z = loc.position.Z
        # From 6 mm below the plate bottom up to the seat, at 1 mm steps.
        z = bb.min.Z - 6.0
        while z <= seat_z + 1e-6:
            head = Pos(0.0, 0.0, z - seat_z) * seated
            r = _residual_vol(part, head)
            assert r < _TRAVEL_TOL, (
                f"entry path blocked at x={loc.position.X:.1f}, z={z:.1f} "
                f"(residual {r:.3f} mm^3 > {_TRAVEL_TOL}) — the head cannot slide "
                "from the bottom aperture to the seat"
            )
            z += 1.0


def assert_retention(part: Part, fx: MountFixtures) -> None:
    """(e) A seated RoundHead pulled straight off the wall (along the mount
    face normal) must FOUL the plate — the narrow lip holds the head's wide
    flange. This is the retention the v3 print lacked: with the pocket carved
    inverted (wide at the open surface) the head pulled straight off and the
    depth-blind checks (a)-(d) all passed anyway. Model-agnostic: fixtures
    only."""
    _require_y_face(fx)
    nx, ny, nz = fx.face_normal
    for loc in fx.seat_locs:
        head = loc * RoundHead()
        assert head.volume > 100.0, "sanity: the library RoundHead is a real solid"
        for dist in _PULL_DISTS:
            pulled = Pos(nx * dist, ny * dist, nz * dist) * head
            r = _residual_vol(part, pulled)
            assert r > _RETENTION_MIN, (
                f"seated head at x={loc.position.X:.1f} pulls off the wall: "
                f"displaced {dist} mm along the mount normal it fouls only "
                f"{r:.3f} mm^3 (need > {_RETENTION_MIN}) — nothing retains the "
                "head (the pocket is likely inverted: wide at the open face)"
            )


def assert_profile(part: Part, fx: MountFixtures) -> None:
    """(f) The slot void must be NARROW at the open (mount) face and WIDE
    inside — the dovetail lip that (e) relies on. Measures the pocket's X span
    just inside the mount face and near its back; the deep span must exceed the
    surface span by >= _PROFILE_MIN_DELTA. Fails on the inverted v3 pocket
    (wide surface, narrow back → negative delta)."""
    _require_z_entry(fx)
    _require_y_face(fx)
    mount_face_y = part.bounding_box().min.Y   # the -Y board face
    for cutter, loc in zip(fx.cutters, fx.seat_locs):
        z = loc.position.Z
        surface = _cutter_x_width(cutter, mount_face_y + _SURFACE_IN, z)
        deep = _cutter_x_width(cutter, mount_face_y + _DEEP_IN, z)
        assert surface > 0.0 and deep > 0.0, (
            f"slot at x={loc.position.X:.1f}: empty width probe "
            f"(surface={surface:.2f}, deep={deep:.2f}) — pocket not where expected"
        )
        assert deep - surface >= _PROFILE_MIN_DELTA, (
            f"slot at x={loc.position.X:.1f} depth profile is not retentive: "
            f"width is {surface:.2f} mm at the open face vs {deep:.2f} mm deep "
            f"(need deep - surface >= {_PROFILE_MIN_DELTA}) — the dovetail must "
            "be narrow at the surface and wide inside, not inverted"
        )


def verify_multiconnect_slot(part: Part, fx: MountFixtures) -> None:
    """Run every multiconnect-slot assertion against a built model."""
    assert_aperture(part, fx)
    assert_orientation(part, fx)
    assert_seat_clearance(part, fx)
    assert_entry_travel(part, fx)
    assert_retention(part, fx)
    assert_profile(part, fx)


def verify_multiconnect_channel(part: Part, fx: MountFixtures) -> None:
    """Normal entry, sub-pitch drop, per-cutter travel and closed top.

    Sample paths at <=0.5 mm, including both endpoints. Each on-ramp pose
    corresponds to a seat. A (seat, on-ramp) pair belongs to exactly one
    cutter: the one whose X centre matches and whose Z extent contains both
    poses, so one X may carry several discrete pockets (pst-93yd5).

    Travel is proved PER CUTTER, from its own lowest on-ramp to its own
    highest seat. A full-height spine is one cutter, so this is its whole
    length; discrete pockets are deliberately NOT joined, because the plate
    between them is meant to be solid. Do not restore a per-X sweep.
    """
    from multibuild.constants import PITCH
    _require_z_entry(fx)
    _require_y_face(fx)
    assert fx.cutters and fx.seat_locs, 'channel fixtures must not be empty'
    assert len(fx.onramp_locs) == len(fx.seat_locs), 'one on-ramp pose per seat required'
    assert_seat_clearance(part, fx)
    assert_retention(part, fx)

    def sweep(head, delta):
        steps = max(1, math.ceil(max(abs(v) for v in delta) / .5))
        for i in range(steps + 1):
            pose = Pos(*(v * i / steps for v in delta)) * head
            residual = _residual_vol(part, pose)
            assert residual < _TRAVEL_TOL, f'channel path blocked: {residual:.3f} mm^3 at step {i}/{steps}'

    for seat, ramp in zip(fx.seat_locs, fx.onramp_locs):
        a, b = seat.position, ramp.position
        assert abs(a.X-b.X) < 1e-7 and abs(a.Y-b.Y) < 1e-7, 'on-ramp must be directly below seat'
        assert 0 < a.Z-b.Z < PITCH, 'seat drop must be less than one pitch'
        head = ramp * RoundHead()
        # Entire head starts outside the board-facing surface.
        distance = head.bounding_box().max.Y - part.bounding_box().min.Y + 1
        sweep(Pos(0, -distance, 0) * head, (0, distance, 0))
        sweep(head, (0, 0, a.Z-b.Z))

    for cutter, pairs in zip(fx.cutters, channel_pairs(fx)):
        bb = cutter.bounding_box()
        x = (bb.min.X + bb.max.X) / 2
        seats, ramps = zip(*pairs)
        # Existing helper expects one cutter per seat; expand only this view.
        assert_profile(part, MountFixtures([cutter] * len(seats), list(seats)))
        low = min(ramps, key=lambda r: r.position.Z)
        high = max(s.position.Z for s in seats)
        sweep(low * RoundHead(), (0, 0, high-low.position.Z))
        assert part.bounding_box().max.Z - bb.max.Z >= 2.4 - 1e-7, 'channel needs a closed top cap'
        # Extrude the actual pocket-back faces through the required backing.
        # This covers the spine, openings and seats locally; unrelated material
        # elsewhere on the model cannot conceal a thin wall behind a channel.
        back_faces = [f for f in cutter.faces().filter_by(Axis.Y)
                      if abs(f.center().Y-bb.max.Y) < 1e-7]
        assert back_faces, 'channel must expose pocket-back faces for backing check'
        # The first 0.5 mm may have the required bed-edge relief. Above it,
        # the whole footprint must have continuous backing, not just its centre.
        floor = max(bb.min.Z, part.bounding_box().min.Z + .5)
        region = Pos(x, bb.max.Y+1.2, (floor+bb.max.Z)/2) * Box(
            bb.size.X+2, 2.4, bb.max.Z-floor)
        for face in back_faces:
            backing = Solid.extrude(face, (0, 2.4, 0)).intersect(region)
            assert backing is not None, 'channel backing probe is empty'
            for probe in backing.solids():
                missing = probe.volume - _residual_vol(part, probe)
                assert missing < 1e-5, f'channel needs >=2.4 mm local backing: {missing:.3f} mm^3 missing'
        # A head trying to ride through the upper end must hit actual material,
        # even when some unrelated geometry makes the global bbox taller.
        top_head = Pos(0, 0, bb.max.Z-low.position.Z) * (low * RoundHead())
        assert _residual_vol(part, top_head) > _RETENTION_MIN, 'head can exit through channel top'
        above = Pos(x, bb.max.Y-2, bb.max.Z+1.2) * Box(4, 2, 2.4)
        assert _residual_vol(part, above) >= above.volume - _EMPTY_VOL, 'channel top is not enclosed'


def channel_pairs(fx: MountFixtures) -> list[list[tuple]]:
    """(seat, on-ramp) pairs per cutter, matched by X centre AND Z extent.

    Every pair must match exactly one cutter and every cutter at least one
    pair. The 1e-7 tolerance matches the X test; a looser one would let two
    abutting pockets both claim a pose on their shared boundary.
    """
    boxes = [c.bounding_box() for c in fx.cutters]
    result = [[] for _ in fx.cutters]
    for seat, ramp in zip(fx.seat_locs, fx.onramp_locs):
        hits = [i for i, bb in enumerate(boxes)
                if abs(seat.position.X - (bb.min.X+bb.max.X)/2) < 1e-7
                and all(bb.min.Z - 1e-7 <= z <= bb.max.Z + 1e-7
                        for z in (seat.position.Z, ramp.position.Z))]
        assert len(hits) == 1, (
            f'seat at x={seat.position.X:.1f}, z={seat.position.Z:.1f} must match '
            f'exactly one channel cutter by X centre and Z extent, matched {len(hits)}')
        result[hits[0]].append((seat, ramp))
    assert all(result), 'every channel needs seat and entry fixtures'
    return result


def verify_openconnect_slot(part: Part, fx: MountFixtures) -> None:
    """openConnect: push in through the on-ramp, shift onto the slot axis,
    slide +Z to a closed seat; pull-off retained; >=2.4 mm backing.

    Fixtures: ``seat_locs`` / ``onramp_locs`` place the openConnect head
    (``openconnect.head()``, not the Multiconnect RoundHead) fully inserted
    at the seat and at the on-ramp. The on-ramp pose sits below the seat and
    may be offset in X (the author's ramp is 2.2 mm to -X); the head is
    pushed in along +Y there, moved across in X, then slid up in Z.
    """
    from openconnect import head as oc_head
    from openconnect.constants import HEAD_WIDTH
    _require_y_face(fx, "openconnect-slot")
    # Express the cardinal slide direction in the existing +Z probe frame.
    # Only this contract supports sideways/downward entry; other mounts keep
    # their existing +Z requirement. The caller's fixtures are not mutated.
    entry = tuple(round(v, 6) for v in fx.entry_axis)
    assert entry in ((0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0)), \
        'openconnect entry_axis must be a cardinal direction in the XZ face'
    if entry != (0, 0, 1):
        undo = Rot(0, -math.degrees(math.atan2(entry[0], entry[2])), 0)
        part = undo * part
        fx = MountFixtures([undo * c for c in fx.cutters],
                           [undo * loc for loc in fx.seat_locs],
                           onramp_locs=[undo * loc for loc in fx.onramp_locs])
    assert fx.cutters and fx.seat_locs, 'openconnect fixtures must not be empty'
    assert len(fx.cutters) == len(fx.seat_locs) == len(fx.onramp_locs), \
        'one cutter, seat and on-ramp pose per slot required'
    fixture = oc_head()

    def sweep(head, delta, step):
        steps = max(1, math.ceil(max(abs(v) for v in delta) / step))
        for i in range(steps + 1):
            pose = Pos(*(v * i / steps for v in delta)) * head
            residual = _residual_vol(part, pose)
            assert residual < _TRAVEL_TOL, (
                f'openconnect entry path blocked: {residual:.3f} mm^3 at step {i}/{steps} '
                f'of {tuple(round(v, 2) for v in delta)}')

    face_y = part.bounding_box().min.Y
    for cutter, seat, ramp in zip(fx.cutters, fx.seat_locs, fx.onramp_locs):
        a, b = seat.position, ramp.position
        assert abs(a.Y - b.Y) < 1e-7, 'on-ramp and seat poses must share the insertion depth'
        assert a.Z > b.Z, 'the on-ramp must be below the seat (heads ride +Z)'
        seated = seat * fixture
        r = _residual_vol(part, seated)
        assert r < _EMPTY_VOL, f'seated openConnect head fouls the model ({r:.3f} mm^3)'
        for dist in _PULL_DISTS:
            r = _residual_vol(part, Pos(0, -dist, 0) * seated)
            assert r > _RETENTION_MIN, (
                f'seated openConnect head pulls off the wall at {dist} mm ({r:.3f} mm^3)')
        r = _residual_vol(part, Pos(0, 0, 1.0) * seated)
        assert r > _OC_END_STOP_MIN, f'slot is open past the seat ({r:.3f} mm^3 at +1 mm)'
        # Entire head starts outside the board-facing surface.
        head = ramp * fixture
        out = head.bounding_box().max.Y - face_y + 0.5
        sweep(Pos(0, -out, 0) * head, (0, out, 0), 0.25)
        sweep(head, (a.X - b.X, 0, 0), 0.25)
        sweep(Pos(a.X - b.X, 0, 0) * head, (0, 0, a.Z - b.Z), 0.5)
        # Dovetail: the mouth is narrower than the head flange, the pocket wider.
        surface = _cutter_x_width(cutter, face_y + 0.2, a.Z)
        bb = cutter.bounding_box()
        deep = _cutter_x_width(cutter, bb.max.Y - 0.3, a.Z)
        assert 0 < surface < HEAD_WIDTH <= deep, (
            f'openconnect pocket is not retentive: {surface:.2f} mm at the face, '
            f'{deep:.2f} mm deep (flange {HEAD_WIDTH})')
        back_faces = [f for f in cutter.faces().filter_by(Axis.Y)
                      if abs(f.center().Y - bb.max.Y) < 1e-7]
        assert back_faces, 'openconnect cutter must expose pocket-back faces'
        for face in back_faces:
            probe = Solid.extrude(face, (0, 2.4, 0))
            missing = probe.volume - _residual_vol(part, probe)
            assert missing < 1e-3, (
                f'openconnect slot needs >=2.4 mm backing: {missing:.3f} mm^3 missing')


_FP_END_STOP_MIN = 5.0  # mm^3: a Fix Point head pushed 1 mm past its seat must
                        #     foul the lip end, not graze it (measured ~20)
_FP_MIN_WEB = 0.9       # mm: material between two pockets (print_audit MIN_WALL_MM)


def verify_fixpoint_slot(part: Part, fx: MountFixtures) -> None:
    """MultiBuild Fix Point slot ([Core] §11, sliding installation): the
    well admits the head straight off the board, the head slides +Z to the
    seat unobstructed, the octagon lip then holds its 45-degree flare (no
    release along the face normal, closed past the seat), >=2.4 mm backing,
    and no two pockets fuse.

    Fixtures: ``seat_locs`` / ``onramp_locs`` place ``multibuild.fixpoint.
    head()`` (the measured Fix Point positive) seated and pushed into the
    well, TRAVEL below the seat at the same X.
    """
    from multibuild.fixpoint import HEAD_FLAT, TRAVEL
    from multibuild.fixpoint import head as fp_head
    _require_z_entry(fx, "multibuild-fixpoint-slot")
    _require_y_face(fx, "multibuild-fixpoint-slot")
    assert fx.cutters and fx.seat_locs, 'fixpoint fixtures must not be empty'
    assert len(fx.cutters) == len(fx.seat_locs) == len(fx.onramp_locs), \
        'one cutter, seat and entry pose per pocket required'
    fixture = fp_head()

    def sweep(head, delta, step):
        steps = max(1, math.ceil(max(abs(v) for v in delta) / step))
        for i in range(steps + 1):
            residual = _residual_vol(part, Pos(*(v * i / steps for v in delta)) * head)
            assert residual < _EMPTY_VOL, (
                f'fixpoint entry path blocked: {residual:.3f} mm^3 at step {i}/{steps} '
                f'of {tuple(round(v, 2) for v in delta)}')

    face_y = part.bounding_box().min.Y
    for cutter, seat, entry in zip(fx.cutters, fx.seat_locs, fx.onramp_locs):
        a, b = seat.position, entry.position
        assert abs(a.X - b.X) < 1e-7 and abs(a.Y - b.Y) < 1e-7, \
            'the entry pose must sit straight below the seat'
        assert abs(a.Z - b.Z - TRAVEL) < 1e-7, 'the head slides TRAVEL up to the seat'
        seated = seat * fixture
        r = _residual_vol(part, seated)
        assert r < _EMPTY_VOL, f'seated Fix Point head fouls the model ({r:.3f} mm^3)'
        # Captured: the lip overlaps the flare, so the head cannot pull off.
        for dist in _PULL_DISTS:
            r = _residual_vol(part, Pos(0, -dist, 0) * seated)
            assert r > _RETENTION_MIN, (
                f'seated Fix Point head pulls off the wall at {dist} mm ({r:.3f} mm^3)')
        r = _residual_vol(part, Pos(0, 0, 1.0) * seated)
        assert r > _FP_END_STOP_MIN, f'slot is open past the seat ({r:.3f} mm^3 at +1 mm)'
        # Entry: from wholly outside the back face straight into the well, then up.
        head = entry * fixture
        out = head.bounding_box().max.Y - face_y + 0.5
        sweep(Pos(0, -out, 0) * head, (0, out, 0), 0.25)
        sweep(head, (0, 0, a.Z - b.Z), 0.25)
        # Lip: narrower than the head at the face, wider behind it.
        surface = _cutter_x_width(cutter, face_y + 0.2, a.Z)
        bb = cutter.bounding_box()
        deep = _cutter_x_width(cutter, bb.max.Y - 0.1, a.Z)
        assert 0 < surface < 2 * HEAD_FLAT <= deep, (
            f'fixpoint pocket is not retentive: {surface:.2f} mm at the face, '
            f'{deep:.2f} mm deep (head {2 * HEAD_FLAT})')
        back_faces = [f for f in cutter.faces().filter_by(Axis.Y)
                      if abs(f.center().Y - bb.max.Y) < 1e-7]
        assert back_faces, 'fixpoint cutter must expose pocket-back faces'
        for face in back_faces:
            probe = Solid.extrude(face, (0, 2.4, 0))
            missing = probe.volume - _residual_vol(part, probe)
            assert missing < 1e-3, (
                f'fixpoint slot needs >=2.4 mm backing: {missing:.3f} mm^3 missing')
    for i, one in enumerate(fx.cutters):
        for other in fx.cutters[i + 1:]:
            gap = one.distance_to(other)
            assert gap >= _FP_MIN_WEB - 1e-6, f'fixpoint pockets fuse: {gap:.2f} mm apart'


def verify_opengrid_snap(part: Part, fx: MountFixtures) -> None:
    """Check an isolated positive snap at each supplied seat pose (not registered).

    BaseSnapSlotCutter in opengrid @eea2b41, base.py:92 defines the minimum
    opening as pitch - 2*(bottom_width + bottom_chamfer): 28-2*(1.1+.4)=25.
    Base (:214) subtracts that cutter; base_1x1 (:399) uses default Base.
    Thus a 24.8 core has .10 mm clearance PER SIDE; no library clearance
    constant exists. OC4b will supply model fixtures and register the contract.
    """
    from opengrid.base import BaseSnapSlotCutter

    opening = BaseSnapSlotCutter()
    width = opening.open_grid_unit_size - 2 * (
        opening.snap_cut_bottom_width + opening.snap_cut_bottom_chamfer)
    # Independently section the actual library cutter at its narrow land.
    land_z = opening.snap_cut_bottom_chamfer + opening.snap_cut_bottom_bump_height / 2
    assert abs(_cutter_x_width(opening, 0, land_z) - width) < 1e-5
    assert fx.seat_locs, 'opengrid-snap needs at least one snap pose'
    for loc in fx.seat_locs:
        local = loc.inverse() * part
        height = local.bounding_box().max.Z
        assert min(abs(height - h) for h in (3.4, 6.8)) < 1e-5
        assert abs(local.bounding_box().min.Z) < 1e-5
        core = section(local, section_by=Plane.XY.offset(height - .7))
        bb = core.bounding_box()
        for low, high in ((bb.min.X, bb.max.X), (bb.min.Y, bb.max.Y)):
            assert abs(low + 12.4) < 1e-5 and abs(high - 12.4) < 1e-5, 'core span must be 24.8'
            assert abs((width - (high - low)) / 2 - .10) <= .05
        # Beyond the 24.8 square only the published click nubs are allowed.
        core_box = Box(24.8, 24.8, height, align=(Align.CENTER, Align.CENTER, Align.MIN))
        extra = height - 3.4
        envelope = core_box
        for angle, depth, span in ((0, .8, 14), (90, .4, 11),
                                   (180, .4, 11), (270, .4, 11)):
            envelope += Rot(0, 0, angle) * Pos(12.4, 0, extra - .01) * Box(
                depth, span, 2.01, align=(Align.MIN, Align.CENTER, Align.MIN))
        outside = local - envelope
        assert sum(s.volume for s in outside.solids()) < 1e-5, 'non-nub material outside core'


# mount type -> contract. Every KNOWN_MOUNTS entry must appear here.
CONTRACTS: dict[str, Callable[[Part, MountFixtures], None]] = {
    "multiconnect-slot": verify_multiconnect_slot,
    "multibuild-multiconnect-slot": verify_multiconnect_slot,
    "multibuild-multiconnect-channel": verify_multiconnect_channel,
    "openconnect-slot": verify_openconnect_slot,
    "multibuild-fixpoint-slot": verify_fixpoint_slot,
}

_uncovered = KNOWN_MOUNTS - CONTRACTS.keys()
assert not _uncovered, (
    f"mount types declared in registry.KNOWN_MOUNTS but missing a contract "
    f"here: {sorted(_uncovered)}"
)


def verify(spec: ModelSpec, mount_type: str, values: dict) -> bool:
    """Top-level entry: resolve fixtures then run the mount's contract.

    Returns False, checking nothing, when the mount is absent under
    ``values`` (registry.ModelSpec.mount_for_values); True once verified."""
    if mount_type not in CONTRACTS:
        raise AssertionError(
            f"{spec.name}: no contract for mount {mount_type!r} "
            f"(known contracts: {sorted(CONTRACTS)})"
        )
    fx = resolve_fixtures(spec, mount_type, values)
    if fx is None:
        return False
    CONTRACTS[mount_type](spec.build(values), fx)
    return True
