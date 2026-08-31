"""Registry-driven toolchain tests — every registered model inherits these."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import trimesh
from build123d import export_stl

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
