"""Registry-driven mount contracts + the self-test negative fixture.

The deterministic contract logic lives in tests/mount_contracts.py; this file
is the harness that auto-parametrizes it over every registered model tagged
with a mount type (like test_toolchain.py does for build/watertight), plus a
NEGATIVE fixture that proves the aperture assertion can actually fail — a
check that never fails guards nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from build123d import Align, Box, Pos, Rotation as Rot  # noqa: E402
from opengrid.multiconnect import SnapInSlotCutter  # noqa: E402

from holders.registry import KNOWN_MOUNTS, MountFixtures, all_models  # noqa: E402
from tests.mount_contracts import (  # noqa: E402
    CONTRACTS,
    assert_aperture,
    assert_profile,
    assert_retention,
    resolve_fixtures,
    verify,
)

# (spec, mount_type) for every registered model that declares a mount — the
# same "for free" wiring as the export/watertight suite.
_MOUNTED = [
    (spec, mount)
    for spec in all_models()
    for mount in spec.mounts
]


def test_every_known_mount_has_a_contract():
    """KNOWN_MOUNTS and CONTRACTS must stay in lockstep (belt-and-braces to the
    import-time assertion in mount_contracts.py)."""
    assert set(KNOWN_MOUNTS) == set(CONTRACTS)


def test_some_model_declares_a_mount():
    """Guard against the parametrization silently collapsing to empty (which
    would make the contract suite vacuously pass)."""
    assert _MOUNTED, "no registered model declares a mount type"


@pytest.mark.parametrize(
    ("spec", "mount"),
    _MOUNTED,
    ids=[f"{s.name}:{m}" for s, m in _MOUNTED],
)
def test_model_mount_contract(spec, mount):
    """Every mount on every registered model must satisfy its contract, at
    default params and at each registered preset."""
    verify(spec, mount, spec.resolve_values())
    for preset in spec.presets:
        verify(spec, mount, spec.resolve_values(preset.values))


# AC 3: the contract must hold over the whole robustness grid — every
# slot_count x slot_travel x snap_notches combination in range. This is the
# guarantee that "every combination yields a mountable plate", not just the
# shipped presets. Only meaningful for multiconnect-slot mounts.
from holders.cylindrical import (  # noqa: E402
    SLOT_TRAVEL_DEFAULT,
    SLOT_TRAVEL_MAX,
    SLOT_TRAVEL_MIN,
)

_GRID = [
    (n, travel, notch)
    for n in (1, 2, 3)
    for travel in (SLOT_TRAVEL_MIN, SLOT_TRAVEL_DEFAULT, SLOT_TRAVEL_MAX)
    for notch in (True, False)
]
_GRID_CASES = [
    (spec, mount, n, travel, notch)
    for spec, mount in _MOUNTED
    if mount == "multiconnect-slot"
    for (n, travel, notch) in _GRID
]


@pytest.mark.parametrize(
    ("spec", "mount", "n", "travel", "notch"),
    _GRID_CASES,
    ids=[
        f"{s.name}:n{n}:t{int(t)}:{'notch' if k else 'plain'}"
        for s, m, n, t, k in _GRID_CASES
    ],
)
def test_mount_contract_over_robustness_grid(spec, mount, n, travel, notch):
    """Every slot_count x slot_travel x snap_notches in range yields a plate
    that hosts the full envelope and keeps all six mount contracts green."""
    values = spec.resolve_values(
        {"slot_count": n, "slot_travel": travel, "snap_notches": notch}
    )
    verify(spec, mount, values)


def test_resolve_fixtures_are_library_geometry():
    """Fixtures a model hands the contract are real, positioned library parts."""
    for spec, mount in _MOUNTED:
        fx = resolve_fixtures(spec, mount, spec.resolve_values())
        assert fx.cutters and fx.seat_locs
        for cutter in fx.cutters:
            assert cutter.volume > 100.0, "cutter is a real pocket solid"


def _sealed_pocket_fixture():
    """A v2-class defect reproduced from library geometry: the SnapInSlotCutter
    placed WITHOUT the -Z flip and high on the plate, so the pocket opens
    toward the TOP and never reaches the bottom edge — a sealed pocket with no
    aperture. Returns (part, fixtures) for the aperture self-test."""
    mount_y = -6.4  # plate spans y in [-6.4, 0]; mount face at min Y
    plate = Pos(0.0, mount_y, 0.0) * Box(
        60.0, 6.4, 60.0, align=(Align.CENTER, Align.MIN, Align.MIN)
    )
    # Base cutter opens at +Z (top), pocket at +Y; placed at z=20 it stays a
    # sealed pocket well above the plate bottom.
    cutter = Pos(0.0, mount_y, 20.0) * SnapInSlotCutter(rotation=(-90, 0, 0))
    part = (plate - cutter).clean()
    seat = Pos(0.0, mount_y, 20.0)  # nominal; aperture check fails before using it
    fx = MountFixtures(cutters=[cutter], seat_locs=[seat], entry_axis=(0.0, 0.0, 1.0))
    return part, fx


def test_negative_sealed_pocket_fails_aperture():
    """The self-test: the v2 sealed-pocket geometry MUST fail the aperture
    assertion. If this ever passes, the aperture check has stopped guarding."""
    part, fx = _sealed_pocket_fixture()
    with pytest.raises(AssertionError, match="aperture"):
        assert_aperture(part, fx)


def _inverted_pocket_fixture():
    """The v3 print defect reproduced from library geometry (bug pst-p07j): the
    SnapInSlotCutter placed with the OLD transform — ``Rot(0, 180, 0) *
    SnapInSlotCutter(rotation=(-90, 0, 0))`` anchored AT the mount face — so
    the dovetail comes out WIDE at the open surface and NARROW inside. Nothing
    retains the head: it pulls straight off the wall. The aperture/orientation/
    seat/travel checks (a)-(d) all PASS on this (the bug shipped and passed CI);
    the retention (e) and profile (f) checks must REJECT it. Returns (part, fx)
    with the same dims as the real spray-can holder (mount_y=-39.4, z_seat=26)."""
    mount_y, z_seat = -39.4, 26.0
    plate = Pos(0.0, mount_y, 0.0) * Box(
        90.0, 6.4, 60.0, align=(Align.CENTER, Align.MIN, Align.MIN)
    )
    cutter = Pos(0.0, mount_y, z_seat) * Rot(0, 180, 0) * SnapInSlotCutter(rotation=(-90, 0, 0))
    part = (plate - cutter).clean()
    seat = Pos(0.0, mount_y, z_seat) * Rot(0, 180, 0) * Rot(-90, 0, 0)
    fx = MountFixtures(
        cutters=[cutter], seat_locs=[seat],
        entry_axis=(0.0, 0.0, 1.0), face_normal=(0.0, -1.0, 0.0),
    )
    return part, fx


def test_negative_inverted_pocket_fails_retention():
    """The v3 inverted pocket MUST fail the retention check — the head pulls
    straight off the wall. Proves (e) catches the exact print-verified defect."""
    part, fx = _inverted_pocket_fixture()
    with pytest.raises(AssertionError, match="retains|pulls off"):
        assert_retention(part, fx)


def test_negative_inverted_pocket_fails_profile():
    """The v3 inverted pocket MUST fail the profile check — wide at the open
    face, narrow inside. Proves (f) catches the exact print-verified defect."""
    part, fx = _inverted_pocket_fixture()
    with pytest.raises(AssertionError, match="inverted|profile"):
        assert_profile(part, fx)


def test_negative_inverted_pocket_still_passes_a_through_d():
    """The inverted pocket passes aperture/orientation/seat/travel — that is
    WHY the v3 bug shipped, and why (e)/(f) had to be added. If any of (a)-(d)
    starts failing here, good, but the point stands: they were depth-blind."""
    from tests.mount_contracts import (
        assert_aperture as _ap,
        assert_orientation as _or,
        assert_seat_clearance as _sc,
        assert_entry_travel as _et,
    )
    part, fx = _inverted_pocket_fixture()
    _ap(part, fx)
    _or(part, fx)
    _sc(part, fx)
    _et(part, fx)
