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
from build123d import Align, Box, Pos  # noqa: E402
from opengrid.multiconnect import SnapInSlotCutter  # noqa: E402

from holders.registry import KNOWN_MOUNTS, MountFixtures, all_models  # noqa: E402
from tests.mount_contracts import (  # noqa: E402
    CONTRACTS,
    assert_aperture,
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
