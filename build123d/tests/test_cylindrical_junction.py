"""Tall, thick collar junction regression and shipped geometry preservation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders import cylindrical
from holders.registry import all_models
from tests.mount_contracts import verify
from tests.print_audit import audit


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
    assert not baseline_report.ok
    assert baseline_report.max_overhang_deg == 90.0
    assert baseline_report.min_wall_mm < 0.9


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
