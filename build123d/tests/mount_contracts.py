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
3. In each model that carries it, tag ``mounts=(...)`` and implement the
   ``mount_fixtures`` hook.
"""
from __future__ import annotations

import importlib
from typing import Callable

from build123d import Align, Box, Pos
from build123d.topology import Part
from opengrid.multiconnect import RoundHead

from holders.registry import KNOWN_MOUNTS, ModelSpec, MountFixtures

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


def _require_z_entry(fx: MountFixtures) -> None:
    ax = tuple(round(a, 6) for a in fx.entry_axis)
    if ax != (0.0, 0.0, 1.0):
        raise AssertionError(
            f"multiconnect-slot contract currently assumes entry_axis=(0,0,1), "
            f"got {fx.entry_axis} — generalize the face/travel probes to extend it"
        )


def _require_y_face(fx: MountFixtures) -> None:
    ax = tuple(round(a, 6) for a in fx.face_normal)
    if ax != (0.0, -1.0, 0.0):
        raise AssertionError(
            f"multiconnect-slot contract currently assumes face_normal=(0,-1,0), "
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
    # Not merely "the whole bottom is missing": the plate is solid at its edge.
    flank = Pos(bb.max.X - 1.0, y_in, z_low) * Box(1.5, 3.0, _SLAB, align=_CENTER3)
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
    for loc in fx.seat_locs:
        x = loc.position.X
        above = Pos(x, y_in, bb.max.Z - 1.0) * Box(4.0, 3.0, _SLAB, align=_CENTER3)
        r = _residual_vol(part, above)
        assert r > _SOLID_MIN, (
            f"plate not solid above the slot at x={x:.1f} (residual {r:.2f} "
            "mm^3) — the channel appears to run out the TOP"
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


# mount type -> contract. Every KNOWN_MOUNTS entry must appear here.
CONTRACTS: dict[str, Callable[[Part, MountFixtures], None]] = {
    "multiconnect-slot": verify_multiconnect_slot,
}

_uncovered = KNOWN_MOUNTS - CONTRACTS.keys()
assert not _uncovered, (
    f"mount types declared in registry.KNOWN_MOUNTS but missing a contract "
    f"here: {sorted(_uncovered)}"
)


def resolve_fixtures(
    spec: ModelSpec, mount_type: str, values: dict
) -> MountFixtures:
    """Fetch a model's ``mount_fixtures`` hook and build fixtures for one mount.

    Fails loudly if a model tagged with a mount does not expose the hook or
    returns geometry-free fixtures (a mislabeled or unbuilt mount).
    """
    module = importlib.import_module(spec.build.__module__)
    hook = getattr(module, "mount_fixtures", None)
    if hook is None:
        raise AssertionError(
            f"{spec.name}: declares mount {mount_type!r} but its module "
            f"{module.__name__} has no mount_fixtures(mount_type, values) hook"
        )
    fx = hook(mount_type, values)
    if not fx.cutters or not fx.seat_locs:
        raise AssertionError(
            f"{spec.name}: mount_fixtures({mount_type!r}) returned no cutters "
            "or seats — the mount is not actually present"
        )
    return fx


def verify(spec: ModelSpec, mount_type: str, values: dict) -> None:
    """Top-level entry: resolve fixtures then run the mount's contract."""
    if mount_type not in CONTRACTS:
        raise AssertionError(
            f"{spec.name}: no contract for mount {mount_type!r} "
            f"(known contracts: {sorted(CONTRACTS)})"
        )
    fx = resolve_fixtures(spec, mount_type, values)
    CONTRACTS[mount_type](spec.build(values), fx)
