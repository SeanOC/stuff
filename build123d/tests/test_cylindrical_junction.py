"""Tall, thick collar junction regression and shipped geometry preservation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build123d import Box, Pos

from holders import cylindrical
from holders.registry import all_models
from tests.mount_contracts import verify
from tests.print_audit import _outward_normal, audit


BASELINE_VOLUMES = {
    "spray_can": 46093.5144299871,
    "spray_can_light": 43166.83316701296,
    "spray_can_robust": 55600.90849424568,
    "bottle_500ml": 47929.49019314198,
    "bottle_500ml_light": 45039.409633779236,
    "bottle_500ml_robust": 57835.443046582965,
}
SPECS = [
    spec for spec in all_models()
    if spec.name in {"holder_spray_can", "holder_bottle_500ml"}
]
CORNER = dict(d=66, h=120, wall=4.0, slot_count=2, slot_travel=45)


def _audit(spec, values, part):
    fixtures = cylindrical.mount_fixtures("multiconnect-slot", values)
    return audit(
        part, spec.print_orientation, cutters=fixtures.cutters, model=spec.name
    )


def test_all_max_junction_prints_and_mounts(monkeypatch):
    spec = next(spec for spec in SPECS if spec.name == "holder_spray_can")
    values = spec.resolve_values(CORNER)
    part = spec.build(values)
    report = _audit(spec, values, part)
    assert report.ok, report.failures()
    assert part.is_valid
    assert len(part.solids()) == 1
    assert part.is_inside((0, 0, cylindrical.FLOOR_DEFAULT / 2))
    for height in (62, 66, 90, 119):
        assert not part.is_inside((0, -33.05, height))
    assert 0 < part.volume - 107966.64921002646 < 20
    verify(spec, "multiconnect-slot", values)

    monkeypatch.setattr(cylindrical, "_reinforce_junction", lambda part, *args: part)
    baseline = spec.build(values)
    baseline_report = _audit(spec, values, baseline)
    # Removing reinforcement is not a printability defect. The old audit
    # reported 90 degrees / 0.131 mm only because this upward plate face's
    # centroid and some UV samples lie inside the continuing collar, outside
    # the trimmed face (pst-h1wy). Preserve the useful gusset independently.
    assert baseline_report.ok, baseline_report.failures()
    assert baseline_report.max_overhang_deg == 45.0
    assert baseline_report.min_wall_mm == pytest.approx(2.25, abs=0.01)
    assert 0 < part.volume - baseline.volume < 20
    plate_top = next(f for f in baseline.faces()
                     if abs(f.center().Z - 61.15) < 1e-6)
    center = plate_top.center()
    assert not plate_top.is_inside(center)
    assert plate_top.normal_at(center).Z == pytest.approx(1)
    assert baseline.is_inside((center.X, center.Y, center.Z + 0.05))
    point, normal = _outward_normal(baseline, plate_top)
    assert plate_top.is_inside(point)
    assert normal.Z == pytest.approx(1)

    # A still-valid bad mutation: cut a side-opening notch through the collar
    # away from the registered mount cutters. Its roof is an actual downward
    # face, with material above and a void below, rather than a centroid in
    # another face's trimmed-away region. The unchanged 45-degree gate must
    # catch this unsupported ceiling on the same baseline holder.
    bad = baseline - Pos(35, 0, 90) * Box(10, 12, 4)
    assert bad.is_valid
    assert len(bad.solids()) == 1
    ceiling_point = (35, 0, 92)
    ceiling = next(f for f in bad.faces() if f.is_inside(ceiling_point))
    assert ceiling.normal_at(ceiling_point).Z == pytest.approx(-1)
    assert bad.is_inside((35, 0, 92.05))
    assert not bad.is_inside((35, 0, 91.95))
    bad_report = _audit(spec, values, bad)
    assert not bad_report.ok
    assert bad_report.max_overhang_deg == 90.0
    assert any(f.startswith("overhang ") for f in bad_report.failures())


@pytest.mark.parametrize(
    "diameter,height,wall,count,travel",
    [
        (66, 90, 3.3, 2, 45),
        (66, 120, 3.6, 2, 45),
        (66, 120, 4, 1, 28),
        (30, 120, 4, 3, 12),
        (120, 120, 4, 3, 45),
    ],
)
def test_tall_thick_junction_sweep(diameter, height, wall, count, travel):
    spec = next(spec for spec in SPECS if spec.name == "holder_spray_can")
    values = spec.resolve_values(dict(
        d=diameter, h=height, wall=wall, slot_count=count, slot_travel=travel
    ))
    part = spec.build(values)
    assert part.is_valid
    assert len(part.solids()) == 1
    report = _audit(spec, values, part)
    assert report.ok, report.failures()


@pytest.mark.parametrize(
    "spec,preset",
    [(spec, preset) for spec in SPECS for preset in spec.presets],
    ids=[preset.id for spec in SPECS for preset in spec.presets],
)
def test_shipped_presets_unchanged_and_printable(spec, preset, monkeypatch):
    reinforce = cylindrical._reinforce_junction
    calls = []

    def unchanged(part, *args):
        result = reinforce(part, *args)
        assert result is part
        calls.append(True)
        return result

    monkeypatch.setattr(cylindrical, "_reinforce_junction", unchanged)
    values = spec.resolve_values(preset.values)
    part = spec.build(values)
    assert calls == [True]
    assert part.volume == pytest.approx(BASELINE_VOLUMES[preset.id], abs=1e-5, rel=0)
    report = _audit(spec, values, part)
    assert report.ok, report.failures()
