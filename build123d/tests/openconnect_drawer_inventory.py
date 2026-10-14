# SPDX-License-Identifier: CC-BY-SA-4.0
"""Geometric inventories for the published drawer; no face-index exemptions."""
from collections import Counter
from math import acos, degrees

import numpy as np
from build123d import Align, Box, Cylinder, Face, Pos, Solid, Wire

from drawer import shell
from drawer import constants as c
from openconnect.constants import EPS
from tests import print_audit as a


def wall_regions(values):
    """Only source-pinned thin fitting floors and shallow slot backing.

    Magnet floor pins at wall=1.6/2.8/4 are .46/1.66/2.86 mm; source meshes
    and normal-direction rays are checked in test_published_wall_inventory.
    The shallow backing floor is .8 mm by the decided mount contract.
    """
    v = values
    d = shell.dimensions(v)
    regions = []
    depth = v.get('shell_side_magnet_thickness', 1)+c.MAGNET_HOLE_DEPTH_CLEARANCE
    radius = v.get('side_magnet_diameter', 6)/2+c.MAGNET_HOLE_SIDE_CLEARANCE
    from build123d import Rot
    orient = Rot(0, 0, 90)*Rot(90, 0, 0)
    slab = orient*Solid.extrude(shell._teardrop(radius), (0, 0, .001))
    for side, (x, y, z) in shell.source_side_magnet_positions(v):
        floor = x+side*(depth-2*EPS)
        regions.append(Pos(floor-.0005, y, z)*slab)
    # Entire published flange-floor family, including its two quarter-rounds.
    # Membership depends on source geometry, never the measured thickness.
    r = c.STOPPER_ROUNDING
    annulus = (Cylinder(r+.0005, c.STOPPER_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN))
               - Cylinder(r-.0005, c.STOPPER_HEIGHT, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    # Height-divider holes ([C] :1634-1644) enter the 2t wall at at+t and end
    # in a t-deep flange-width pocket (hole_excess=t) whose ceiling sits at
    # at-2*EPS (the shaft overshoot): the same t-0.8 flange floor, seen from
    # the flange and from the pocket (at shell_thickness 1.6 both read 0.8 mm).
    divider_tops = [(x, at+d.wall, z) for axis, at in shell.divider_walls(v) if axis == 'y'
                    for x, _, z in shell.source_stopper_positions(v)]
    for x, y, z in divider_tops:
        regions.append(Pos(x, y-d.wall-2*EPS, z+c.STOPPER_HEIGHT/2)
                       *Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, .001, c.STOPPER_HEIGHT))
    for x, y, z in shell.source_stopper_positions(v)+divider_tops:
        regions.append(Pos(x, y-c.STOPPER_FLANK_DEPTH, z+c.STOPPER_HEIGHT/2)
                       *Box(c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH, .001, c.STOPPER_HEIGHT))
        for side in (-1, 1):
            centre_x = x+side*(c.STOPPER_WIDTH/2+r)
            centre_y = y-c.STOPPER_FLANK_DEPTH-r
            quadrant = Pos(-side*r/2, r/2, c.STOPPER_HEIGHT/2)*Box(r+.001, r+.001, c.STOPPER_HEIGHT)
            regions.append(Pos(centre_x, centre_y, z)*(annulus & quadrant))
    if v.get('shell_to_slot_wall_thickness', .9) < .9:
        # The interior box face corresponding to the chosen slot plate.
        # Tests exercise .8 mm, while .6/.7 are named errors before modelling.
        if d.slot_face == 'Back':
            regions.append(Pos(0, 0, d.slot_thickness-.0005)*Solid.extrude(
                shell._section(d.inner_width, d.inner_height, d.inner_chamfer), (0, 0, .001)))
        elif d.slot_face in ('Top', 'Bottom'):
            sign = 1 if d.slot_face == 'Top' else -1
            regions.append(Pos(0, sign*d.inner_height/2, d.slot_thickness+d.inner_depth/2)
                           *Box(d.inner_width, .001, d.inner_depth))
        else:
            sign = 1 if d.slot_face == 'Right' else -1
            regions.append(Pos(sign*d.inner_width/2, 0, d.slot_thickness+d.inner_depth/2)
                           *Box(.001, d.inner_height, d.inner_depth))
    return [shell.AUTHOR_TO_MODEL*r for r in regions]


def source_contact_mask(points, values, classifier):
    """Reference CSG skins at three precisely scoped source interfaces.

    :1388 leaves a coincident front cap in the Top reference. :1468 and
    :1816-1821 leave coincident flange-mouth and flange-shaft faces. These
    are zero-material surfaces, unlike the surrounding physical boundaries.
    Both sides must be void in the exact solid; the source coordinates and
    independent reference ray probes are separately pinned by tests.
    """
    d = shell.dimensions(values)
    points = np.asarray(points)
    candidates = np.zeros(len(points), dtype=bool)
    directions = np.zeros_like(points)
    if d.slot_face == 'Top':
        x, y, z = points.T
        region = ((np.abs(z-d.depth) < 1e-5)
                  & (np.abs(x) <= d.inner_width/2) & (np.abs(y) <= d.inner_height/2)
                  & (np.abs(x)+np.abs(y) <= (d.inner_width+d.inner_height)/2-d.inner_chamfer))
        candidates |= region
        directions[region, 2] = .01
    # Divider walls repeat the top wall's stopper holes at their +Y face.
    divider_tops = [(x, at+d.wall, z) for axis, at in shell.divider_walls(values) if axis == 'y'
                    for x, _, z in shell.source_stopper_positions(values)]
    for x, y, z in shell.source_stopper_positions(values)+divider_tops:
        for plane in (y, y-c.STOPPER_FLANK_DEPTH):
            region = ((np.abs(points[:, 1]-plane) < 1e-5)
                      & (np.abs(points[:, 0]-x) <= (c.STOPPER_WIDTH+c.STOPPER_FLANK_WIDTH)/2)
                      & (points[:, 2] >= z-1e-5) & (points[:, 2] <= z+c.STOPPER_HEIGHT+1e-5))
            candidates |= region
            directions[region] = (0, .01, 0)
    result = np.zeros(len(points), dtype=bool)
    for i in np.flatnonzero(candidates):
        p, delta = points[i], directions[i]
        result[i] = not classifier.is_inside(p+delta) and not classifier.is_inside(p-delta)
    return result


def edge_inventory(part, values):
    """Classify every non-tangent edge by its geometric/source family.

    Published exterior long edges and front rims: source :1474-1480.
    Container mating cavity corners/base: :1372/:1388. Magnets/stoppers:
    :1433-1469. Library profiles retain their own functional edges.
    Every other sharp edge fails; no whole-model or thickness-based waiver.
    """
    source = shell.AUTHOR_TO_MODEL.inverse()*part
    d = shell.dimensions(values)
    fx = shell.slot_fixtures(values)
    mount_boxes = a._cutter_boxes([shell.AUTHOR_TO_MODEL.inverse()*cut for cut in fx.cutters])
    fitting_boxes = a._cutter_boxes(shell.source_magnet_cutters(values)+shell.source_stopper_cutters(values)
                                    +shell.source_divider_feature_cutters(values), margin=.001)
    original = shell.source_body(values)
    honeycomb = [(hole.bounding_box(), hole.faces())
                 for hole in shell.source_honeycomb_cutters(values)]
    divider_faces = [(f, f.bounding_box()) for wall in shell.source_divider_walls(values)
                     for f in wall.faces()]
    corner_points = [(v.X, v.Y) for v in original.vertices()]
    base_edges = [e for e in original.edges() if
                  abs(e.bounding_box().min.Z-d.slot_thickness)<1e-6 and
                  abs(e.bounding_box().max.Z-d.slot_thickness)<1e-6]
    front_edges = [e for e in original.edges() if
                   abs(e.bounding_box().min.Z-d.depth)<1e-6 and
                   abs(e.bounding_box().max.Z-d.depth)<1e-6]
    adjacent = {}
    for face in source.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)
    counts = Counter()
    worst = 0.
    for edge, faces in adjacent.items():
        if len(faces) != 2:
            continue  # periodic seams have no second physical surface
        mid = edge.position_at(.5)
        n0, n1 = (face.normal_at(mid) for face in faces)
        angle = degrees(acos(max(-1., min(1., n0.dot(n1)))))
        if angle < 1:
            continue
        points = [edge.position_at(t) for t in (0, .5, 1)]
        bb = edge.bounding_box()
        if bb.max.Z <= .301:
            family = 'bed bevel'
        elif all(a._in_any_box(*tuple(p), mount_boxes) for p in points):
            family = 'library mount'
        elif all(a._in_any_box(*tuple(p), fitting_boxes) for p in points):
            family = 'magnet/stopper fit'
        elif any(all(box.min.X-1e-5 <= p.X <= box.max.X+1e-5 and
                     box.min.Y-1e-5 <= p.Y <= box.max.Y+1e-5 and
                     box.min.Z-1e-5 <= p.Z <= box.max.Z+1e-5 and
                     min(face.distance_to(p) for face in hole_faces) < 1e-5
                     for p in points) for box, hole_faces in honeycomb):
            family = 'source/roofed honeycomb opening'
        elif (max(abs(p.Z-d.depth) for p in points) < 1e-5 and
              all(min(e.distance_to(p) for e in front_edges) < 1e-5 for p in points)):
            family = 'published front rim'
        elif (bb.size.X < 1e-5 and bb.size.Y < 1e-5 and
              any(abs(mid.X-x)<1e-5 and abs(mid.Y-y)<1e-5 for x, y in corner_points)):
            family = 'published longitudinal corner'
        elif (max(abs(p.Z-d.slot_thickness) for p in points) < 1e-5 and
              all(min(e.distance_to(p) for e in base_edges) < 1e-5 for p in points)):
            family = 'container mating base'
        elif divider_faces and all(any(
                box.min.X-1e-5 <= p.X <= box.max.X+1e-5 and box.min.Y-1e-5 <= p.Y <= box.max.Y+1e-5
                and box.min.Z-1e-5 <= p.Z <= box.max.Z+1e-5 and face.distance_to(p) < 1e-5
                for face, box in divider_faces) for p in points):
            # [C] :1576-1673 (D4): square 2*shell_thickness walls, their front
            # rims and their junctions with the shell, as the author's.
            family = 'published divider wall'
        else:
            raise AssertionError(f'uninventoried edge at {tuple(mid)}, angle {angle:.3f}, bounds {bb}')
        counts[family] += 1
        if family not in ('library mount', 'magnet/stopper fit'):
            worst = max(worst, angle)
    return dict(counts), worst


# ---------------------------------------------------------------- container

def _prism(polygon, z0, z1):
    """Shapely polygon in author XY, extruded along author Z."""
    face = Face(Wire.make_polygon([(x, y, z0) for x, y in list(polygon.exterior.coords)[:-1]],
                                  close=True))
    return Solid.extrude(face, (0, 0, z1-z0))


def label_plate_tips(values):
    """60-degree corners of the strut-aligned label plates ([C] :1783-1793)
    that stick into a front cell: ((x, y), unit bisector into the plate),
    author frame."""
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from drawer import container
    plates = unary_union(container.label_fills(values))
    walls = [layout for name, _, layout, _ in container.wall_layouts(values) if name == 'Front']
    if plates.is_empty or not walls:
        return []
    openings = unary_union(walls[0].openings)
    tips = []
    for polygon in getattr(plates, 'geoms', [plates]):
        ring = list(polygon.exterior.coords)[:-1]
        for i, (x, y) in enumerate(ring):
            (px, py), (nx, ny) = ring[i-1], ring[(i+1) % len(ring)]
            a, b = np.array([px-x, py-y]), np.array([nx-x, ny-y])
            a, b = a/np.linalg.norm(a), b/np.linalg.norm(b)
            angle = degrees(acos(np.clip(a@b, -1, 1)))
            # Convex (material) corner: the bisector points into the plate.
            bisector = (a+b)/np.linalg.norm(a+b)
            convex = polygon.contains(Point(np.array((x, y))+.01*bisector))
            if angle < 89 and convex and openings.distance(Point(x, y)) < 1e-6:
                tips.append(((x, y), tuple(bisector)))
    return tips


def back_magnet_rims(values):
    """Back magnet teardrops whose flat cap (radius + .2, [C] :1564) ends
    within MIN_WALL of the back wall's top (:429): at vertical_grids 1 the
    grid offset (:1453-1456) leaves a 0.2 mm skin over the cap across the
    hole depth, pinned by the container-2x1x5 reference ray. Only those
    holes are emitted, as the band from MIN_WALL below the cap to the top
    over the hole depth: ((x, cap gap), region), author frame."""
    from drawer import container
    v = values or {}
    d = container.dimensions(v)
    top = -d.height/2+d.back_height
    rims = []
    for (kind, _, (x, _, _)), cut in zip(container.source_magnet_positions(v),
                                         container.source_magnet_cutters(v)[0]):
        box = cut.bounding_box()
        if kind != 'back' or top-box.max.Y >= a.MIN_WALL_MM:
            continue
        size = (box.size.X+2*a.MIN_WALL_MM, top-box.max.Y+a.MIN_WALL_MM+.001, box.size.Z+.001)
        rims.append(((x, top-box.max.Y), Pos(x, top+.001-size[1]/2, box.max.Z/2-.0005)
                     * Box(*size)))
    return rims


def container_wall_regions(values):
    """Source-pinned thin regions of the container (exception rows).

    Magnet floors: hole depth (thickness + .15) into the wall leaves the
    author's floor, .45 mm behind a 1.6 Solid wall (:1546-1564). The label
    holder is built from LABEL_WALL = .8 (:1779). The label plates' 60-degree
    corners poke into front cells (:1783-1793). Back magnet rims: see
    back_magnet_rims. Reference rays pin all four in
    test_published_thin_features; membership is geometric.
    """
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from drawer import container
    v = values or {}
    d = container.dimensions(v)
    regions = []
    for (kind, side, (x, y, z)), cut in zip(container.source_magnet_positions(v),
                                            container.source_magnet_cutters(v)[0]):
        # The floor is the cutter's inner end face; the slab behind it runs
        # to the inner surface: wall - hole, or the bulge's .45 + EPS
        # (:1547/:1561), +-.0005 mm.
        inward = np.array((0, 0, 1) if kind == 'back' else (-side, 0, 0))
        floor = max(cut.faces(), key=lambda f: np.dot(tuple(f.center()), inward))
        wall = d.back if kind == 'back' else d.side
        hole = v.get(f'container_{kind}_magnet_thickness', 1)+.15
        behind = max(wall-hole, .45+EPS)+.001
        regions.append(Pos(*(-inward*.0005))*Solid.extrude(floor, tuple(inward*behind)))
    regions += [box for _, box in back_magnet_rims(v)]
    holder = container.source_label_holder(v)
    if holder is not None:
        regions.append(holder)
    plates = unary_union(container.label_fills(v))
    for (x, y), _ in label_plate_tips(v):
        regions.append(_prism(Point(x, y).buffer(2).intersection(plates),
                              d.depth-d.front-.001, d.depth+.001))
    return [container.AUTHOR_TO_MODEL*r for r in regions]


def container_edge_inventory(part, values):
    """Classify every non-tangent container edge by source family.

    Walls, rims, outer chamfers and fillet junctions: :1484-1500/:1528-1535
    (`_envelope - _cavity`). Handle :1675-1773 and label holder :1774-1806
    including their junctions with the front. Honeycomb openings (source
    cells, D2 roofs and fills) and magnet fits :1546-1564. Every other sharp
    edge fails; no thickness-based waiver. Returns (family counts, worst
    convex edge angle outside the magnet fits).
    """
    from drawer import container
    v = values or {}
    d = container.dimensions(v)
    source = container.AUTHOR_TO_MODEL.inverse()*part
    plain = container._envelope(d)-container._cavity(d)
    plain_edges = plain.edges()
    cuts, bulges = container.source_magnet_cutters(v)
    fitting_boxes = a._cutter_boxes(cuts+bulges, margin=.001)
    def boxed(shapes):
        return [(face, face.bounding_box()) for shape in shapes for face in shape.faces()]

    honeycomb = boxed(container.source_honeycomb_wall_cutters(v))
    plain_edges = [(e, e.bounding_box()) for e in plain_edges]
    features = [(name, boxed([shape])) for name, shape in (
        ('source handle', container.source_handle(v)),
        ('source label holder', container.source_label_holder(v))) if shape is not None]
    # [C] :1576-1673 (D4): square-edged 1.2 mm walls with foot fillets; their
    # junctions with walls and openings lie on the divider's own faces.
    features += [('source divider wall', boxed([wall])) for wall in container.source_divider_walls(v)]

    def near(p, items):
        return any(box.min.X-1e-5 <= p.X <= box.max.X+1e-5 and
                   box.min.Y-1e-5 <= p.Y <= box.max.Y+1e-5 and
                   box.min.Z-1e-5 <= p.Z <= box.max.Z+1e-5 and
                   item.distance_to(p) < 1e-5 for item, box in items)

    adjacent = {}
    for face in source.faces():
        for edge in face.edges():
            adjacent.setdefault(edge, []).append(face)
    counts = Counter()
    worst = 0.
    bed = -d.height/2+.301
    for edge, faces in adjacent.items():
        if len(faces) != 2:
            continue
        mid = edge.position_at(.5)
        n0, n1 = (face.normal_at(mid) for face in faces)
        angle = degrees(acos(max(-1., min(1., n0.dot(n1)))))
        if angle < 1:
            continue
        points = [edge.position_at(t) for t in (0, .5, 1)]
        if edge.bounding_box().max.Y <= bed:
            family = 'bed bevel'
        elif all(a._in_any_box(*tuple(p), fitting_boxes) for p in points):
            family = 'magnet fit'
        elif all(near(p, honeycomb) for p in points):
            family = 'source/roofed honeycomb opening'
        elif all(near(p, plain_edges) for p in points):
            family = 'published wall edge'
        elif all(near(p, plain_edges) or near(p, honeycomb) for p in points):
            # container_inner_fillet=0: the front window inset (side+fillet,
            # bottom+fillet; [C] :1501-1527) lands on the cavity corner, so
            # the inner corner edge runs on through the window unbroken.
            family = 'published wall edge'
        else:
            for name, feature_faces in features:
                if all(near(p, feature_faces) for p in points):
                    family = name
                    break
            else:
                raise AssertionError(f'uninventoried edge at {tuple(mid)}, angle {angle:.3f}, '
                                     f'bounds {edge.bounding_box()}')
        counts[family] += 1
        # Report convex (material) edges: a concave air-slot corner such as
        # the 15-degree gap beside a 45-degree roof is not an exposed edge.
        tangent = edge.tangent_at(.5)
        inward = tangent.cross(n0).normalized()
        if faces[0].distance_to(mid+inward*.001) > 1e-4:
            inward = -inward
        if family != 'magnet fit' and n1.dot(inward) < 0:
            worst = max(worst, angle)
    return dict(counts), worst


def container_skin_mask(points, normals, values, classifier):
    """Reference CSG skins on the back-inner and front-inner wall planes.

    The author fuses each wall panel into the walls with attach(...,
    inside=true) (:1502-1527); CGAL leaves their coincident +-Y faces inside
    the bottom and side walls. Mesh frame (author_to_mesh). Only samples on
    those two planes, normal along Y, with material on BOTH sides in the
    exact port qualify; a physical boundary always has air on one side.
    """
    from drawer import container
    d = container.dimensions(values)
    points, normals = np.asarray(points), np.asarray(normals)
    plane = np.zeros(len(points), dtype=bool)
    for y in (-d.back, -(d.depth-d.front)):
        plane |= np.abs(points[:, 1]-y) < 1e-4
    candidates = plane & (np.abs(normals[:, 1]) > .999)
    result = np.zeros(len(points), dtype=bool)
    for i in np.flatnonzero(candidates):
        p, n = points[i], .01*normals[i]
        result[i] = classifier.is_inside(p+n) and classifier.is_inside(p-n)
    return result
