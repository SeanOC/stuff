"""holder_bench_projector_mount: the bench projector saddle mount (pst-czxuk.4, flat top pst-czxuk.5/.6)."""
import math

import pytest
from build123d import Axis, Rectangle, Pos, Vector

from holders import bench_lip_clip
from holders.bench_lip_clip import lip_clip_profile
from holders.bench_projector_mount import (BOSS_CHAMFER, HOLE_FLOOR, INSERT_WALL, LIP_PARAMS, PARAMS, SPEC,
                                           _flat_dimensions, audit_exclusions, bridges, dimensions, holder,
                                           mount_profile)
from holders.printer import BED_X, BED_Y, BED_Z
from tests.audit_record import record
from tests.print_audit import MAX_BRIDGE_MM, audit

NUMERIC = [q for q in PARAMS if q.kind == 'number']
RIB_ONLY = {'rib_height', 'rib_wall', 'rib_spacing', 'boss_od'}
FLAT_ONLY = {'adapter_thread', 'recess_d', 'recess_depth'}
FLAT = {'top': 'flat'}

# §6 item 3: every numeric endpoint plus the documented corners. An endpoint
# another guard makes unreachable at the defaults is an expected-ValueError
# row; its nearest reachable corner is listed in CORNERS.
EXPECTED_ERRORS = {
    ('wall', 3): 'wall - lead_in',                 # 3 - 1.5 < 1.6
    ('wall', 8): 'plate must be >= wall',          # the 6 mm plate would not cover the jaw
    ('lead_in', 3): 'cheek_wall - lead_in',        # 4 - 3 < 1.6
    ('bench_width', 315): 'reduce bench_width',    # 5 + 319 + 4 = 328 > BED_X
    ('cheek_wall', 3): 'cheek_wall - lead_in',     # 3 - 1.5 < 1.6
    ('boss_od', 13): 'boss_od',                    # 8.2 + 5 = 13.2
    ('insert_hole', 10): 'boss_od',                # 10.2 + 5 > 14
    ('insert_length', 20): 'plate \\+ rib_height',  # 6 + 15 - 21 < 2
}
# The same sweep at top=flat (rib_* and boss_od are skipped there).
FLAT_EXPECTED_ERRORS = {
    ('wall', 3): 'wall - lead_in',
    ('wall', 8): 'plate must be >= wall',
    ('lead_in', 3): 'cheek_wall - lead_in',
    ('bench_width', 315): 'reduce bench_width',
    ('cheek_wall', 3): 'cheek_wall - lead_in',
    ('recess_d', 12): 'recess_d must be',         # 8.2 + 5 + 2 = 15.2
}
CORNERS = [
    {'wall': 3, 'lead_in': 1.0},                                   # thinnest reachable C wall
    {'wall': 8, 'plate': 8, 'width_clearance': 2},                 # thickest C wall: 324
    {'lead_in': 3, 'cheek_wall': 5},                               # longest lead-in
    {'lead_in': 0, 'wall': 3, 'cheek_wall': 3},                    # square tips, thinnest walls
    {'bench_width': 315, 'width_clearance': 1, 'cheek_wall': 3, 'lead_in': 1},  # widest: 324
    {'width_clearance': 6, 'cheek_wall': 6},                       # 5 + 316 + 6 = 327: refused
    {'boss_od': 13.2},                                             # thinnest insert wall
    {'boss_od': 13, 'insert_hole': 7.8},                           # boss_od min, reachable
    {'insert_hole': 10, 'hole_compensation': 0.5, 'boss_od': 24},  # largest hole
    {'insert_length': 20, 'rib_height': 17},                       # deepest hole, floor exactly 2
    {'insert_length': 20, 'rib_height': 25, 'plate': 10},          # deepest hole, tallest stack
    {'rib_height': 10, 'plate': 5, 'insert_length': 6},            # shortest stack
    {'length': 80, 'boss_z_offset': -27},                          # boss tip 3 mm from the bed end
    {'length': 80, 'boss_z_offset': 29},                           # boss 3 mm from the top end
    {'length': 200, 'boss_z_offset': 45},
    {'boss_x_offset': -100, 'rib_spacing': 100, 'boss_od': 24, 'rib_wall': 8},  # ribs near the front
    {'boss_x_offset': 100, 'rib_spacing': 30, 'rib_wall': 8, 'bench_width': 250},  # ribs vs boss gap
    {'slab_thickness': 31, 'height_clearance': -0.5, 'hook_depth': 6, 'lead_in': 0, 'cheek_depth': 6},
    {'slab_thickness': 70, 'height_clearance': 4, 'hook_depth': 20, 'cheek_depth': 20,
     'jaw_root_radius': 2, 'edge_gap': 2},
]
FLAT_CORNERS = [{**FLAT, **c} for c in [
    {'recess_d': 15.2},                                            # thinnest floor ring round the insert
    {'recess_d': 13, 'insert_hole': 6, 'hole_compensation': 0},    # recess_d min, reachable
    {'recess_d': 24, 'insert_hole': 10, 'hole_compensation': 0.5},  # widest recess and hole
    {'plate': 10, 'recess_depth': 1, 'insert_length': 6, 'adapter_thread': 6},  # shallowest: deck top = plate top
    {'recess_depth': 30, 'adapter_thread': 25, 'recess_d': 24},    # tallest slab, widest recess
    {'boss_x_offset': -100, 'bench_width': 250, 'recess_d': 24},   # recess nearest the front
    {'boss_x_offset': 100, 'bench_width': 250, 'recess_d': 24},    # recess nearest the rear
    {'length': 80, 'boss_z_offset': -27},                          # recess + chamfer 3 mm from the bed end
    {'length': 80, 'boss_z_offset': 27},                           # recess + chamfer 3 mm from the top end
    {'length': 300, 'boss_z_offset': 45},
    {'wall': 8, 'plate': 8, 'width_clearance': 2},                 # thickest C wall: 324
    {'lead_in': 0, 'wall': 3, 'cheek_wall': 3},                    # square tips, thinnest walls
]]
REFUSED = [c for c in CORNERS if c == {'width_clearance': 6, 'cheek_wall': 6}]
ENDPOINTS = [{q.name: v} for q in NUMERIC if q.name not in FLAT_ONLY for v in (q.min, q.max)
             if (q.name, v) not in EXPECTED_ERRORS]
FLAT_ENDPOINTS = [{**FLAT, q.name: v} for q in NUMERIC if q.name not in RIB_ONLY for v in (q.min, q.max)
                  if (q.name, v) not in FLAT_EXPECTED_ERRORS]
CASES = [{}] + ENDPOINTS + [c for c in CORNERS if c not in REFUSED] + [FLAT] + FLAT_ENDPOINTS + FLAT_CORNERS \
    + [p.values for p in SPEC.presets]


def _id(values):
    return ','.join(f'{k}={v}' for k, v in values.items()) or 'defaults'


def _inside(sketch, x, y):
    return any(f.is_inside(Vector(x, y, 0), tolerance=1e-6) for f in sketch.faces())


def _lip(p):
    return bench_lip_clip.dimensions({**{k: p[k] for k in LIP_PARAMS}, 'top_reach': p['lip']['top_reach']})


def assert_profile(p):
    """Probes 0.01 mm either side of each functional face."""
    s, e = mount_profile(p), 0.01
    w, ys, yt, xr = p['wall'], p['slab_top'], p['plate_top'], p['rear_x']
    mid = (p['edge_x'] + xr)/2
    # Plate: underside on the slab top, plate thick.
    assert not _inside(s, mid, ys - e) and _inside(s, mid, ys + e)
    assert _inside(s, p['edge_x'] + 1, yt - e) and yt - ys == pytest.approx(p['plate'])
    # Rear cheek: inner face at wall + bench_width + width_clearance, cheek_depth deep.
    y = ys - (p['cheek_depth'] + p['lead_in'] - p['jaw_root_radius'])/2
    assert not _inside(s, xr - e, y) and _inside(s, xr + e, y)
    assert xr - w == pytest.approx(p['bench_width'] + p['width_clearance'])
    tip = xr + (p['cheek_wall'] + p['lead_in'])/2
    assert _inside(s, tip, ys - p['cheek_depth'] + e) and not _inside(s, tip, ys - p['cheek_depth'] - e)
    if p['top'] == 'flat':
        # One solid slab from the slab top to the deck top, cheek to cheek
        # (pst-czxuk.6): no hollow, no channel, nothing outside it.
        W, yr = p['width'], p['height']
        for x in (2, p['edge_x'] + 1, mid, xr - 1, W - 2):
            assert _inside(s, x, yr - e) and not _inside(s, x, yr + e)
            assert all(_inside(s, x, ys + e + k*(yr - ys - 2*e)/8) for k in range(9))
        assert not _inside(s, -e, (ys + yr)/2) and not _inside(s, W + e, (ys + yr)/2)
        assert p['height'] - p['slab_top'] == pytest.approx(p['recess_depth'] + p['pocket'] + HOLE_FLOOR)
    else:
        # Ribs: rib_wall wide, rib_height tall, centred on rib_x.
        for x in p['rib_x']:
            t = p['rib_wall']/2
            assert _inside(s, x, p['height'] - e) and not _inside(s, x, p['height'] + e)
            yy = yt + p['rib_height']/2
            assert _inside(s, x - t + e, yy) and not _inside(s, x - t - e, yy)
            assert _inside(s, x + t - e, yy) and not _inside(s, x + t + e, yy)
    bb = s.bounding_box()
    assert bb.size.X == pytest.approx(p['footprint'][0]) and bb.size.Y == pytest.approx(p['footprint'][1])
    assert p['footprint'][0] <= BED_X and p['footprint'][1] <= BED_Y and p['length'] <= BED_Z


def assert_lip_c_identical(p):
    """Below the slab top, the front cheek IS lip_clip_profile at the same params."""
    window = Pos(p['edge_x'] + p['bench_width']/4 - 1, p['slab_top']/2 - 0.5) \
        * Rectangle(p['edge_x'] + p['bench_width']/2 + 2, p['slab_top'] + 1)
    mine, ref = mount_profile(p) & window, lip_clip_profile(_lip(p)) & window
    assert ref.area > 0
    assert (mine - ref).area == pytest.approx(0, abs=1e-6)
    assert (ref - mine).area == pytest.approx(0, abs=1e-6)


def assert_insert(part, p):
    """The insert hole: hole_d across, hole_depth deep, a floor clear of the slab.

    Flat top: the hole opens on the recess floor (recess_d across,
    recess_depth deep, a flat floor), and the slab is solid all round both
    bores and through both ends.
    """
    bx, bz, e = p['boss_x'], p['boss_z'], 0.01

    def solid(x, yy, z):
        return part.is_inside(Vector(x, yy, z))

    def bore(r, top, depth):
        y = top - depth/2
        assert not solid(bx - r + e, y, bz) and solid(bx - r - e, y, bz)
        assert not solid(bx + r - e, y, bz) and solid(bx + r + e, y, bz)
        assert not solid(bx, y, bz - r + e) and solid(bx, y, bz - r - e)
        assert not solid(bx, y, bz + r - e) and solid(bx, y, bz + r + e)   # the flat roof: tall = 2r
    r = p['hole_d']/2
    bore(r, p['hole_top'], p['hole_depth'])
    floor = p['hole_top'] - p['hole_depth']
    assert not solid(bx, floor + e, bz) and solid(bx, floor - e, bz)
    assert floor - p['slab_top'] >= HOLE_FLOOR - 1e-9
    if p['top'] == 'flat':
        assert p['hole_depth'] == pytest.approx(max(p['insert_length'], p['adapter_thread']) + 1)
        assert floor - p['slab_top'] == pytest.approx(HOLE_FLOOR)
        R = p['recess_d']/2
        assert p['recess_d'] >= p['hole_d'] + 2*INSERT_WALL + 2 - 1e-9
        bore(R, p['height'], p['recess_depth'])
        ring = bx + (r + R)/2 + 0.4   # the floor between the hole's mouth chamfer and the recess wall
        assert not solid(ring, p['recess_floor'] + e, bz) and solid(ring, p['recess_floor'] - e, bz)
        assert p['height'] - p['recess_floor'] == pytest.approx(p['recess_depth'])
        mid = (p['slab_top'] + p['height'])/2
        for xc in (bx - R - INSERT_WALL, bx + R + INSERT_WALL, p['edge_x'] + 10, p['rear_x'] - 10):
            assert all(solid(xc, mid, z) for z in (1, bz, p['length'] - 1))   # no hollow, no channel
    else:
        assert p['hole_depth'] == pytest.approx(p['insert_length'] + 1)
        assert p['boss_od'] >= p['hole_d'] + 2*INSERT_WALL - 1e-9
        # Boss outer wall along X, at mid-height.
        R, y = p['boss_r'], (p['plate_top'] + p['boss_top'])/2
        assert solid(bx + R - e, y, bz) and not solid(bx + R + e, y, bz)


def assert_finished_edges(part, p):
    """Edge classifier (the bench_lip_clip / width-saddle pattern).

    bore: the insert hole's floor and (flat top) the recess floor, sharp by
    function (the insert seats on one, the adapter's body on the other). tangent: fillet runs. eased: every other edge, dihedral < 90
    degrees (45 degree chamfers and lead-ins). tip: lead_in 0 only, the hook
    and rear cheek tips' square inner corners. No other class exists.
    """
    tips = [] if p['lead_in'] else [(p['lip']['hook_x'], p['wall']),
                                    (p['rear_x'], p['slab_top'] - p['cheek_depth'])]
    floors = [(p['hole_top'] - p['hole_depth'], p['hole_d']/2 + 1e-3)]
    if p['top'] == 'flat':
        floors.append((p['recess_floor'], p['recess_d']/2 + 1e-3))
    adjacency = {}
    for f in part.faces():
        for edge in f.edges():
            adjacency.setdefault(edge, []).append(f)
    counts, worst = {'bore': 0, 'tangent': 0, 'eased': 0}, 0.0
    for edge, faces in adjacency.items():
        assert len(faces) == 2
        c = edge.center()
        if any(abs(c.Y - floor) < 1e-6 and abs(c.X - p['boss_x']) < r and -r < c.Z - p['boss_z'] < r*math.sqrt(2)
               for floor, r in floors):
            counts['bore'] += 1
            continue
        if any(abs(c.X - x) < 1e-6 and abs(c.Y - y) < 1e-6 for x, y in tips):
            counts['tip'] = counts.get('tip', 0) + 1
            continue
        n0, n1 = (f.normal_at(c) for f in faces)
        angle = math.degrees(math.acos(max(-1, min(1, n0.dot(n1)))))
        if angle < 1e-3:
            counts['tangent'] += 1
        else:
            assert angle < 90 - 1e-3, (tuple(c), angle)
            counts['eased'] += 1
            worst = max(worst, angle)
    assert all(counts.values()) and counts.get('tip', 0) == len(tips), counts
    bed = min(part.faces().filter_by(lambda f: f.normal_at().Z < -0.99), key=lambda f: f.center().Z)
    for edge in bed.edges():
        other = next(f for f in adjacency[edge] if f != bed)
        assert other.normal_at(edge.center()).Z == pytest.approx(-math.sqrt(.5), abs=1e-4)
    return counts, worst


def assert_bridges(part, p, values):
    """Each exclusion box holds exactly its one flat ceiling, measured first."""
    raw = audit(part, SPEC.print_orientation, model=SPEC.name)
    assert raw.longest_bridge_mm <= MAX_BRIDGE_MM
    for (name, z, x0, x1, y0, y1), box in zip(bridges(p), audit_exclusions(values)):
        inside = [f for f in part.faces()
                  if all(box[i] <= v <= box[i + 3] for b in [f.bounding_box()]
                         for i, v in enumerate((b.min.X, b.min.Y, b.min.Z)))
                  and all(box[i] <= v <= box[i + 3] for b in [f.bounding_box()]
                          for i, v in enumerate((b.max.X, b.max.Y, b.max.Z)))]
        assert len(inside) == 1, (name, len(inside))
        f = inside[0]
        assert f.geom_type.name == 'PLANE' and f.normal_at().Z == pytest.approx(-1)
        assert f.bounding_box().size.X == pytest.approx(x1 - x0, abs=1e-3)
        assert x1 - x0 <= MAX_BRIDGE_MM


@pytest.mark.parametrize('values', [{}] + ENDPOINTS + CORNERS + [FLAT] + FLAT_ENDPOINTS + FLAT_CORNERS, ids=_id)
def test_profile_dimensions(values):
    if values in REFUSED:
        with pytest.raises(ValueError, match='reduce bench_width'):
            dimensions(values)
        return
    p = dimensions(values)
    assert p['inner_height'] == pytest.approx(p['slab_thickness'] + p['height_clearance'])
    assert_profile(p)
    assert_lip_c_identical(p)


@pytest.mark.parametrize('top,key,message', [('ribbed', k, m) for k, m in sorted(EXPECTED_ERRORS.items())]
                         + [('flat', k, m) for k, m in sorted(FLAT_EXPECTED_ERRORS.items())], ids=lambda v: str(v))
def test_unreachable_endpoints_raise(top, key, message):
    with pytest.raises(ValueError, match=message):
        dimensions({'top': top, key[0]: key[1]})


@pytest.mark.parametrize('values,message', [
    ({'width_clearance': 1, 'edge_gap': 0.6}, 'width_clearance - edge_gap'),
    ({'width_clearance': 1, 'edge_gap': 0.5}, None),
    ({'width_clearance': 6}, None),                                    # 5 + 316 + 4 = 325 = BED_X
    ({'bench_width': 314, 'width_clearance': 3}, None),               # 5 + 317 + 4 = 326 ... refused below
    ({'cheek_depth': 6, 'lead_in': 2.5, 'cheek_wall': 5}, 'cheek_depth - lead_in - jaw_root_radius'),
    ({'hook_depth': 6, 'lead_in': 3.5}, 'lead_in must be in'),
    ({'hook_depth': 6, 'lead_in': 3, 'cheek_wall': 5}, None),            # hook flat exactly 3
    ({'slab_thickness': 31, 'height_clearance': -1.5}, 'height_clearance must be in'),
    ({'slab_thickness': 31, 'height_clearance': -0.5}, None),
    ({'plate': 5, 'wall': 5.5}, 'plate must be >= wall'),
    ({'length': 80, 'boss_z_offset': -28}, 'boss_z_offset'),
    ({'length': 80, 'boss_z_offset': 30}, 'boss_z_offset'),
    ({'rib_spacing': 30, 'boss_od': 20}, 'rib_spacing'),
    ({'boss_x_offset': -100, 'rib_spacing': 150}, 'off the plate'),
    ({'insert_length': 20, 'rib_height': 16.5}, 'plate \\+ rib_height'),
    ({'length': 301}, 'length'),
    ({'nope': 1}, 'unknown'),
    ({'top': 'round'}, 'top must be one of'),
    ({'top': 'flat', 'recess_d': 15}, 'recess_d must be'),
    ({'top': 'flat', 'recess_d': 15.2}, None),
    ({'top': 'flat', 'length': 80, 'boss_z_offset': -28}, 'puts the recess'),
    ({'top': 'flat', 'length': 80, 'boss_z_offset': 28}, 'puts the recess'),
    ({'top': 'flat', 'length': 80, 'boss_z_offset': -24, 'recess_d': 24}, None),
    ({'top': 'flat', 'length': 80, 'boss_z_offset': -25, 'recess_d': 24}, 'puts the recess'),
    # top=flat skips the rib and boss guards (invariant 3).
    ({'top': 'flat', 'rib_spacing': 30, 'boss_od': 20}, None),
    ({'top': 'flat', 'insert_length': 20, 'rib_height': 10}, None),
    ({'top': 'flat', 'boss_x_offset': -100, 'rib_spacing': 150}, None),
])
def test_guards_name_the_parameter(values, message):
    if values == {'bench_width': 314, 'width_clearance': 3}:
        message = 'reduce bench_width'
    if message is None:
        dimensions(values)
        return
    with pytest.raises(ValueError, match=message):
        dimensions(values)


def test_defaults_are_the_spec():
    """Sean 2026-10-29: 38 + 0.2 lip, 310 + 4 width, 11.5 deep, 8.0 + 0.2 hole 13.7 deep."""
    p = dimensions({})
    assert p['inner_height'] == pytest.approx(38.2) and p['inner_width'] == pytest.approx(314)
    assert p['hook_depth'] == p['cheek_depth'] == 11.5
    assert p['hole_d'] == pytest.approx(8.2) and p['hole_depth'] == pytest.approx(13.7)
    assert p['boss_od'] >= 13.0 and p['plate'] == 6 and p['rib_height'] == 15 and p['rib_wall'] == 4
    assert p['length'] == 120 and p['footprint'] == pytest.approx((323, 64.2))
    assert p['boss_x'] == pytest.approx(p['edge_x'] + 155) and p['boss_z'] == pytest.approx(60)
    # The default sits under its own range ceiling (plan review advisory 3).
    assert next(q for q in PARAMS if q.name == 'width_clearance').max > p['width_clearance']
    assert p['top'] == 'ribbed'


def test_flat_defaults_are_the_spec():
    """pst-czxuk.5 rev 3: the measured adapter (body 16 x 4, 8 mm threads); pst-czxuk.6: no deck params."""
    p = dimensions(FLAT)
    assert (p['recess_d'], p['recess_depth'], p['adapter_thread']) == (18, 6, 8)
    assert not {'deck_width', 'deck_skin', 'deck_wall'} & {q.name for q in PARAMS}
    assert p['pocket'] == pytest.approx(13.7) and p['deck_top'] == pytest.approx(21.7)
    assert p['deck_height'] == pytest.approx(15.7) and p['footprint'] == pytest.approx((323, 64.9))
    assert p['boss_r'] == pytest.approx(9)   # the recess circle


def test_recess_side_guard():
    """The recess stays INSERT_WALL from either side of the slab. Unreachable in the
    declared ranges (>= 16 mm of slab beside it), so drive the guard directly."""
    p = dimensions(FLAT)
    r = p['recess_d']/2
    for bx in (r + INSERT_WALL - 0.1, p['width'] - r - INSERT_WALL + 0.1):
        with pytest.raises(ValueError, match='of a side of the slab'):
            _flat_dimensions(dict(p), p['hole_d'], bx, p['boss_z'])
    for bx in (r + INSERT_WALL, p['width'] - r - INSERT_WALL):
        _flat_dimensions(dict(p), p['hole_d'], bx, p['boss_z'])


# Main @5904e848 (pst-czxuk.4): the ribbed presets must not move (invariant 1).
RIBBED_IDENTITY = {'short-80': (191649.37609476488, (323.0, 64.2, 80.0)),
                   'long-200': (476927.87162933074, (323.0, 64.2, 200.0))}


@pytest.mark.parametrize('preset', sorted(RIBBED_IDENTITY))
def test_ribbed_presets_unchanged(preset):
    values = next(p.values for p in SPEC.presets if p.id == preset)
    part = holder(**values)
    volume, size = RIBBED_IDENTITY[preset]
    bb = part.bounding_box()
    assert part.volume == pytest.approx(volume, rel=1e-9)
    assert tuple(bb.size) == pytest.approx(size, abs=1e-6) and tuple(bb.min) == pytest.approx((0, 0, 0), abs=1e-6)


def test_presets_and_slug():
    assert SPEC.slug == 'holder-bench-projector-mount'
    assert [p.id for p in SPEC.presets] == ['short-80', 'long-200', 'flat-250']
    assert SPEC.presets[2].values == {'top': 'flat', 'length': 250}


@pytest.mark.parametrize('values', [{}, FLAT] + [p.values for p in SPEC.presets],
                         ids=['defaults', 'flat'] + [p.id for p in SPEC.presets])
def test_insert_and_bridges(values):
    p = dimensions(values)
    part = holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    assert_insert(part, p)
    assert_bridges(part, p, values)
    # Root and top of the boss are chamfered, never filleted.
    assert BOSS_CHAMFER >= 1.0
    assert part.bounding_box().size.Z == pytest.approx(p['length'])


@pytest.mark.audit
@pytest.mark.parametrize('values', CASES, ids=_id)
def test_endpoint_audit(values):
    p = dimensions(values)
    part = holder(**values)
    assert part.is_valid and len(part.solids()) == 1
    counts, edge = assert_finished_edges(part, p)
    report = audit(part, SPEC.print_orientation, exclusions=audit_exclusions(values), model=SPEC.name)
    assert report.ok, report.format()
    assert not report.downward_fillets
    record('bench-projector-mount-endpoint', case=_id(values), min_wall=report.min_wall_mm,
           max_overhang=report.max_overhang_deg, exposed_edge_angle=edge, volume=part.volume, ok=report.ok,
           **counts)
    print(f"ENDPOINT {_id(values)}: min_wall={report.min_wall_mm:.3f} "
          f"overhang={report.max_overhang_deg:.1f} edge={edge:.1f} {counts} volume={part.volume:.0f} ok={report.ok}")
