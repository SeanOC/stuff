"""Registry-driven toolchain tests — every registered model inherits these."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import trimesh

from scripts.export import export_stl
from holders.registry import all_models

SPECS = all_models()


def test_library_dims_opengrid_tile():
    """Sanity-pin the library's openGrid dims (28mm grid, 6.8mm height)."""
    from opengrid.base import Base
    bb = Base().bounding_box()
    assert round(bb.size.X, 3) == 28.0
    assert round(bb.size.Y, 3) == 28.0
    assert round(bb.size.Z, 3) == 6.8


@pytest.mark.parametrize("spec", SPECS, ids=[s.name for s in SPECS])
def test_model_builds_and_is_manifold(spec, tmp_path):
    part = spec.build(spec.resolve_values())
    assert part.volume > 0
    stl = tmp_path / f"{spec.name}.stl"
    export_stl(part, str(stl))
    mesh = trimesh.load_mesh(stl)
    assert mesh.is_watertight, f"{spec.name}: exported STL is not watertight"
    assert mesh.volume > 0


def test_pointed_cone_export_removes_only_collapsed_triangles(tmp_path):
    import numpy as np
    from build123d import Align, Box, Cone, Pos, Rot, export_stl as native_export
    cone = Pos(25, 0, 0) * Rot(90, 0, 0) * Cone(
        3.55, 0, 3.55, align=(Align.CENTER, Align.CENTER, Align.MIN))
    part = cone.fuse(Box(70, 5, 30, align=(Align.CENTER, Align.MIN, Align.CENTER)))
    raw_path, clean_path = tmp_path/'raw.stl', tmp_path/'clean.stl'
    native_export(part, str(raw_path))
    export_stl(part, clean_path)
    raw, clean = trimesh.load_mesh(raw_path), trimesh.load_mesh(clean_path)
    f = raw.faces
    keep = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0])
    assert not keep.all(), 'fixture must exercise the native cone-apex artifact'
    assert clean.is_watertight and clean.is_winding_consistent
    # Every retained triangle is bit-for-bit native geometry. No mesh repair
    # fills a real hole or replaces the zero-diameter cone tip with a flat.
    assert np.array_equal(clean.triangles, raw.triangles[keep])
    assert clean.volume == pytest.approx(raw.volume, abs=1e-9)
    assert np.array_equal(clean.bounds, raw.bounds)
