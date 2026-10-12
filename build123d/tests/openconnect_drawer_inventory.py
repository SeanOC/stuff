# SPDX-License-Identifier: CC-BY-SA-4.0
"""Geometric inventories for the published drawer; no face-index exemptions."""
from collections import Counter
from math import acos, degrees

import numpy as np
from build123d import Align, Box, Cylinder, Face, Pos, Solid

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
    for x, y, z in shell.source_stopper_positions(v):
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
    for x, y, z in shell.source_stopper_positions(values):
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
    fitting_boxes = a._cutter_boxes(shell.source_magnet_cutters(values)+shell.source_stopper_cutters(values), margin=.001)
    original = shell.source_body(values)
    honeycomb = [(hole.bounding_box(), hole.faces())
                 for hole in shell.source_honeycomb_cutters(values)]
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
            family = 'published honeycomb opening'
        elif (max(abs(p.Z-d.depth) for p in points) < 1e-5 and
              all(min(e.distance_to(p) for e in front_edges) < 1e-5 for p in points)):
            family = 'published front rim'
        elif (bb.size.X < 1e-5 and bb.size.Y < 1e-5 and
              any(abs(mid.X-x)<1e-5 and abs(mid.Y-y)<1e-5 for x, y in corner_points)):
            family = 'published longitudinal corner'
        elif (max(abs(p.Z-d.slot_thickness) for p in points) < 1e-5 and
              all(min(e.distance_to(p) for e in base_edges) < 1e-5 for p in points)):
            family = 'container mating base'
        else:
            raise AssertionError(f'uninventoried edge at {tuple(mid)}, angle {angle:.3f}, bounds {bb}')
        counts[family] += 1
        if family not in ('library mount', 'magnet/stopper fit'):
            worst = max(worst, angle)
    return dict(counts), worst
