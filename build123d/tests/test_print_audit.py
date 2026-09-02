"""Deterministic printability audit — hard synthetic self-tests + the
registry-driven advisory run (bead pst-jfyb).

Two layers, mirroring test_mount_contracts.py:

* **Synthetic self-tests** (always gating): purpose-built solids at known
  geometry pin every threshold — a 50° overhang fails and a 40° passes, a
  12 mm bridge fails and an 8 mm passes, a 0.8 mm wall fails and a 1.2 mm
  passes, a bottom fillet fails and a bottom chamfer passes, and a library
  cutter's pocket is excluded. A check that cannot fail guards nothing.
* **Registry-driven run** (ADVISORY): every registered model is audited at
  its declared print orientation, the report printed, and — until the flag
  below flips — a failure is an ``xfail`` rather than a hard failure. This
  is the design-guidelines §1 rules made standing instead of eyeballed.

Flip ``PRINT_AUDIT_REQUIRED = True`` (one line) to make the registry run a
hard gate once the holder passes its own audit (design-guidelines §6 / AC 3).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math  # noqa: E402

import pytest  # noqa: E402
from build123d import (  # noqa: E402
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Line,
    Plane,
    Pos,
    extrude,
    make_face,
)
from opengrid.multiconnect import SnapInSlotCutter  # noqa: E402

from holders.registry import all_models  # noqa: E402
from tests.mount_contracts import resolve_fixtures  # noqa: E402
from tests.print_audit import (  # noqa: E402
    MAX_BRIDGE_MM,
    MAX_OVERHANG_DEG,
    MIN_WALL_MM,
    PrintAuditReport,
    audit,
)

# One-line switch (AC 3): False = advisory (xfail on failure, report printed);
# True = the registry-driven audit is a hard gate. Kept advisory until the
# production holders pass their own audit — they miss §1 at every orientation
# today (a round collar on its side has real overhangs), so the geometry fix +
# a declared print_orientation + this flip all land together as "holder v5"
# (follow-up bead pst-xz3m). See build123d/README.md → Print audit.
PRINT_AUDIT_REQUIRED = False

# Generous per-model ceiling for AC 1 ("< 60 s each"); the real cost is ~0.1 s.
_PER_MODEL_BUDGET_S = 60.0

_UP_Z = (0.0, 0.0, 1.0)


def _unit(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


# --- synthetic solids at known geometry -----------------------------------

def _overhang_wedge(overhang_deg: float) -> Box:
    """A prism whose one downward-facing planar face sits at exactly
    ``overhang_deg`` from vertical (0 = vertical wall, 90 = flat ceiling).

    Cross-section in X-Z (extruded along Y): a short bed edge, then a face
    rising at the target angle. The rising face B→C faces down-and-out, so
    its outward normal has a downward component of ``sin(overhang_deg)``."""
    rise = 10.0
    run = rise * math.tan(math.radians(overhang_deg))
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Line((0, 0), (5, 0))
                Line((5, 0), (5 + run, rise))
                Line((5 + run, rise), (0, rise))
                Line((0, rise), (0, 0))
            make_face()
        extrude(amount=30)
    return bp.part


def _bridge_model(gap_mm: float) -> Box:
    """A flat slab on two legs with an unsupported span of ``gap_mm`` — the
    slab's exposed underside is a downward flat ceiling ``gap_mm`` wide."""
    leg_w, length, slab_t, leg_h = 5.0, 30.0, 3.0, 10.0
    slab = Pos(0, 0, leg_h) * Box(
        gap_mm + 2 * leg_w, length, slab_t, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    left = Pos(-(gap_mm / 2 + leg_w / 2), 0, 0) * Box(
        leg_w, length, leg_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    right = Pos(+(gap_mm / 2 + leg_w / 2), 0, 0) * Box(
        leg_w, length, leg_h, align=(Align.CENTER, Align.CENTER, Align.MIN)
    )
    return slab + left + right


def _wall_box(thickness_mm: float) -> Box:
    """A slab whose thinnest dimension is ``thickness_mm``."""
    return Box(thickness_mm, 20.0, 20.0)


def _plate_with_pocket() -> tuple[Box, SnapInSlotCutter]:
    """A back plate with one real library ``SnapInSlotCutter`` pocket, carved
    the same way the holder does. The pocket's angled dovetail faces are steep
    downward overhangs — which the audit must ignore once the cutter envelope
    is supplied (the slot profile is spec)."""
    mount_y = -6.4
    plate = Pos(0, mount_y, 0) * Box(
        60.0, 6.4, 60.0, align=(Align.CENTER, Align.MIN, Align.MIN)
    )
    cutter = Pos(0, mount_y + 4.15, 26.0) * SnapInSlotCutter(rotation=(90, 0, 0))
    part = (plate - cutter).clean()
    return part, cutter


# --- overhang (AC 2) ------------------------------------------------------

def test_overhang_50deg_fails():
    report = audit(_overhang_wedge(50.0), _UP_Z, model="wedge50")
    assert report.max_overhang_deg == pytest.approx(50.0, abs=0.5)
    assert report.max_overhang_deg > MAX_OVERHANG_DEG
    assert not report.ok


def test_overhang_40deg_passes():
    report = audit(_overhang_wedge(40.0), _UP_Z, model="wedge40")
    assert report.max_overhang_deg == pytest.approx(40.0, abs=0.5)
    assert report.max_overhang_deg <= MAX_OVERHANG_DEG
    # 40° wedge has no bridge, thick walls, no bottom fillet → fully printable
    assert report.ok, report.format()


# --- bridge (AC 2) --------------------------------------------------------

def test_bridge_12mm_fails():
    report = audit(_bridge_model(12.0), _UP_Z, model="bridge12")
    assert report.longest_bridge_mm == pytest.approx(12.0, abs=0.5)
    assert report.longest_bridge_mm > MAX_BRIDGE_MM
    assert not report.ok


def test_bridge_8mm_passes():
    report = audit(_bridge_model(8.0), _UP_Z, model="bridge8")
    assert report.longest_bridge_mm == pytest.approx(8.0, abs=0.5)
    assert report.longest_bridge_mm <= MAX_BRIDGE_MM


# --- wall thickness (AC 2) ------------------------------------------------

def test_wall_0p8mm_fails():
    report = audit(_wall_box(0.8), _UP_Z, model="wall0.8")
    assert report.min_wall_mm == pytest.approx(0.8, abs=0.05)
    assert report.min_wall_mm < MIN_WALL_MM
    assert not report.ok


def test_wall_1p2mm_passes():
    report = audit(_wall_box(1.2), _UP_Z, model="wall1.2")
    assert report.min_wall_mm == pytest.approx(1.2, abs=0.05)
    assert report.min_wall_mm >= MIN_WALL_MM


# --- downward fillet vs chamfer (AC 2) ------------------------------------

def _bottom_edges(box: Box):
    return box.edges().group_by(Axis.Z)[0]


def test_bottom_fillet_fails():
    box = Box(20, 20, 10)
    filleted = box.fillet(radius=2.0, edge_list=_bottom_edges(box))
    report = audit(filleted, _UP_Z, model="bottom_fillet")
    assert report.downward_fillets, "a bottom fillet must be flagged"
    assert all("CYLINDER" in d.geom_type or d.geom_type != "PLANE"
               for d in report.downward_fillets)
    assert not report.ok


def test_bottom_chamfer_passes():
    box = Box(20, 20, 10)
    chamfered = box.chamfer(length=0.4, length2=0.4, edge_list=_bottom_edges(box))
    report = audit(chamfered, _UP_Z, model="bottom_chamfer")
    assert not report.downward_fillets, "a 45° chamfer is planar, not a fillet"
    assert report.max_overhang_deg <= MAX_OVERHANG_DEG + 1e-6
    assert report.bed_chamfer == "present"
    assert report.ok, report.format()


# --- library cutter envelope exclusion (AC 2) -----------------------------

def test_library_cutter_pocket_is_excluded():
    part, cutter = _plate_with_pocket()
    # Without the cutter envelope, the pocket's dovetail faces trip overhang.
    unexcluded = audit(part, _UP_Z, model="pocket_raw")
    assert unexcluded.max_overhang_deg > MAX_OVERHANG_DEG, (
        "sanity: the raw pocket should look like an overhang"
    )
    # With the library cutter supplied, its envelope is excluded → clean.
    excluded = audit(part, _UP_Z, cutters=[cutter], model="pocket_excluded")
    assert excluded.max_overhang_deg <= MAX_OVERHANG_DEG, excluded.format()
    assert not excluded.downward_fillets


# --- report shape (AC 1) --------------------------------------------------

def test_report_is_typed_and_formats():
    report = audit(_wall_box(1.2), _UP_Z, model="shape")
    assert isinstance(report, PrintAuditReport)
    assert report.orientation == (0.0, 0.0, 1.0)
    assert report.bed_chamfer in ("present", "absent", "n/a")
    text = report.format()
    assert "print audit: shape" in text
    assert "overhang" in text and "bridge" in text and "min wall" in text


def test_empty_part_raises():
    with pytest.raises(ValueError):
        audit(Box(1, 1, 1) - Box(2, 2, 2), _UP_Z, model="void")


# --- registry-driven run (AC 1 + AC 3, advisory) --------------------------

_SPECS = all_models()


def _audit_model(spec) -> PrintAuditReport:
    """Audit a registered model at its declared print orientation, excluding
    every declared mount's library-cutter envelopes."""
    values = spec.resolve_values()
    part = spec.build(values)
    cutters: list = []
    for mount in spec.mounts:
        cutters.extend(resolve_fixtures(spec, mount, values).cutters)
    return audit(part, spec.print_orientation, cutters=cutters, model=spec.name)


@pytest.mark.parametrize("spec", _SPECS, ids=[s.name for s in _SPECS])
def test_model_audit_produces_report_within_budget(spec):
    """AC 1: every registered model yields a typed report in < 60 s."""
    start = time.time()
    report = _audit_model(spec)
    elapsed = time.time() - start
    assert isinstance(report, PrintAuditReport)
    assert report.orientation == tuple(round(o, 6) for o in
                                       _unit(spec.print_orientation))
    assert elapsed < _PER_MODEL_BUDGET_S, (
        f"{spec.name}: audit took {elapsed:.1f}s (budget {_PER_MODEL_BUDGET_S}s)"
    )


@pytest.mark.parametrize("spec", _SPECS, ids=[s.name for s in _SPECS])
def test_model_print_audit(spec, capsys):
    """AC 3: advisory printability audit over every registered model. The
    report is printed; a failure is an xfail until PRINT_AUDIT_REQUIRED flips."""
    report = _audit_model(spec)
    with capsys.disabled():
        print("\n" + report.format())
    if report.ok:
        return
    reason = f"advisory print audit not yet gating for {spec.name}:\n{report.format()}"
    if PRINT_AUDIT_REQUIRED:
        pytest.fail(reason)
    pytest.xfail(reason)
