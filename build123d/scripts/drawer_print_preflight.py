"""Compare drawer shell print poses and pin the reference's cavity ceiling.

Run from build123d/: uv run python scripts/drawer_print_preflight.py
This measures the unfinished body primitive and a patch of the mayor mesh;
it does not claim a finished-model or endpoint audit.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import trimesh
from trimesh.ray.ray_util import contains_points

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'build123d'))

from build123d import Pos, Rot
from drawer import shell
from tests.print_audit import _max_local_span, audit


def measure():
    path = ROOT / 'assets/openConnect-drawer/mesh/shell-top-slot-solid.stl'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == '9d7986a17f436b11f7dc28dcd607d230a0bd4136ae742c0a296bb998846da1c1'
    ref = trimesh.load_mesh(path)
    values = {'shell_slot_position': 'Top'}
    part = shell.body(values)
    d = shell.dimensions(values)
    # Source +Y is the Top mount face. With that face down, -Y is print up.
    top_down = Pos(0, 0, d.source_y+d.height/2)*Rot(-90, 0, 0)*shell.AUTHOR_TO_MODEL.inverse()
    back_down = shell.AUTHOR_TO_MODEL.inverse()

    # A 120 x 120 mm patch inside the opposite wall, away from every mount,
    # magnet, stopper and side-wall feature. Plane and ray are SCAD-frame.
    step = 3.0
    xs = np.arange(-60+step/2, 60, step)
    zs = np.arange(10+step/2, 130, step)
    points = np.array([(x, -25.6, z) for x in xs for z in zs])
    above = points + (0, -.1, 0)
    below = points + (0, .1, 0)
    # Fix the ray direction rather than using trimesh's fallback random ray.
    solid_above = contains_points(ref.ray, above, check_direction=(0, 1, 0))
    void_below = ~contains_points(ref.ray, below, check_direction=(0, 1, 0))
    grid = (solid_above & void_below).reshape(len(xs), len(zs))
    assert grid.all(), 'reference ceiling patch drifted'
    intersections, _, _ = ref.ray.intersects_location([[0, 0, 70]], [[0, -1, 0]])
    return {
        'reference': str(path.relative_to(ROOT)), 'reference_sha256': digest,
        'reference_ray_origin': [0, 0, 70], 'reference_ray_direction': [0, -1, 0],
        'reference_ray_intersections': sorted(intersections.tolist()),
        'reference_ceiling_patch': {
            'source_x': [-60, 60], 'source_z': [10, 130], 'source_y': -25.6,
            'probe_mm': .1, 'grid_step_mm': step,
            'unsupported_cells': int(grid.sum()), 'total_cells': int(grid.size),
            'measured_local_span_lower_bound_mm': _max_local_span(grid.tolist(), step),
            'span_method': 'tests.print_audit._max_local_span on mesh solid-above / void-below samples',
        },
        'body_stage': 'Box and chamfered cavity BEFORE feature cuts and bed treatment; not a finished model audit',
        'slot_face_down': asdict(audit(part, print_frame=top_down)),
        'back_wall_down': asdict(audit(part, print_frame=back_down)),
    }


if __name__ == '__main__':
    print(json.dumps(measure(), indent=2))
