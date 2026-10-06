"""Parameter-dependent print placement across audit, bake, review and live export."""
import importlib.util
import io
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from build123d import Align, Box, Pos, Rot

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from holders import gridfinity_shelf
from holders.registry import in_print_frame
from scripts import export
from scripts.thumbnail import PlaneSpec
from tests.print_audit import audit


@pytest.fixture
def spec():
    return replace(gridfinity_shelf.SPEC, name='print_frame_probe', mounts=(),
                   build=lambda values: Box(4, 6, 8, align=(Align.MIN,)*3),
                   print_frame=lambda values: Pos(0, 8, 0)*Rot(90, 0, 0),
                   review_sections=(PlaneSpec((1, 2, 3), (0, 0, 1), 'probe'),))


def assert_printed(part):
    assert tuple(part.bounding_box().min) == pytest.approx((0, 0, 0))
    assert tuple(part.bounding_box().size) == pytest.approx((4, 8, 6))


def test_identity_returns_original_shape(spec):
    part = spec.build({})
    assert in_print_frame(replace(spec, print_frame=None), {}, part) is part


def test_audit_applies_frame_before_classification(spec):
    part = spec.build({})
    expected = audit(in_print_frame(spec, {}, part))
    actual = audit(part, print_frame=spec.print_frame({}))
    assert actual == expected


def test_review_transforms_geometry_and_section_once(spec, monkeypatch, tmp_path):
    monkeypatch.setattr(export, 'all_models', lambda: [spec])
    monkeypatch.setattr(export, 'OUT', tmp_path)
    monkeypatch.setattr(export, 'export_stl', lambda part, path: assert_printed(part))
    monkeypatch.setattr(export, 'export_glb', lambda part, path, colours: assert_printed(part))
    captured = []
    monkeypatch.setattr(export, 'render_review', lambda glb, png, ctx: captured.append(ctx))
    assert export.export_all() == 0
    plane = captured[0].sections[0]
    assert plane.origin == pytest.approx((1, 5, 2))
    assert plane.normal == pytest.approx((0, -1, 0))


def test_bake_applies_frame(spec, monkeypatch, tmp_path):
    monkeypatch.setattr(export, 'all_models', lambda: [spec])
    parts = []
    monkeypatch.setattr(export, 'export_stl', lambda part, path: parts.append(part))
    monkeypatch.setattr(export, 'export_glb', lambda part, path, colours: assert_printed(part))
    monkeypatch.setattr(export, 'render_thumbnail', lambda glb, png: None)
    assert export.export_presets_only(tmp_path) == 0
    assert len(parts) == 4
    for part in parts:
        assert_printed(part)


def test_live_export_applies_frame(spec, monkeypatch, tmp_path):
    import holders.registry as registry
    path = Path(__file__).resolve().parents[2]/'services'/'bd-render'/'render_worker.py'
    module_spec = importlib.util.spec_from_file_location('frame_worker', path)
    worker = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(worker)
    target = tmp_path/'live.stl'
    monkeypatch.setattr(sys, 'argv', [str(path), spec.slug, 'stl', str(target)])
    monkeypatch.setattr(sys, 'stdin', io.StringIO('{}'))
    monkeypatch.setattr(registry, 'all_models', lambda: [spec])
    def write(part, path):
        assert_printed(part)
        Path(path).write_bytes(b'frame-tested')
    monkeypatch.setattr(export, 'export_stl', write)
    assert worker.main() == 0


def test_mount_contract_stays_in_model_frame(spec, monkeypatch):
    from holders.registry import MountFixtures
    from tests import mount_contracts
    fx = MountFixtures([Box(1, 1, 1)], [Pos()])
    monkeypatch.setattr(mount_contracts, 'resolve_fixtures', lambda *args: fx)
    def check(part, actual):
        assert actual is fx
        assert tuple(part.bounding_box().size) == pytest.approx((4, 6, 8))
    monkeypatch.setitem(mount_contracts.CONTRACTS, 'frame-test', check)
    assert mount_contracts.verify(spec, 'frame-test', {})
