"""Open-rear tray, printed front face down (Z=0); rack up is +Y.

Worst load is device weight along -Y, bending the floor away from the front
face. Full-height tapered side webs carry that bending into the ears. PLA
or PCTG; avoid hot equipment beyond the printed material's service limits.
"""
from math import ceil, isfinite
from build123d import Align, Box, Face, Pos, Vector, Wire, extrude, fillet
from . import constants as c
from .panel import finish, panel, panel_height


class TrayFitError(ValueError):
    """Device and rails cannot fit the rack opening or selected U height."""


def tray_dimensions(device_w, device_d, device_h, units=None, clearance=1.0):
    if not all(isfinite(v) and v > 0 for v in (device_w, device_d, device_h)):
        raise TrayFitError('device_w, device_d and device_h must be finite and positive')
    if not isfinite(clearance) or not .5 <= clearance <= 2:
        raise TrayFitError('clearance must be 0.5..2 mm')
    inner = device_w+2*clearance
    outer = inner+2*c.RAIL_WALL
    if outer > c.TRAY_OUTER_WIDTH_LIMIT+1e-9:
        raise TrayFitError(f'tray fit: device_w + 2*clearance + 2*rail wall = {outer:g} mm exceeds {c.TRAY_OUTER_WIDTH_LIMIT:g} mm')
    required = device_h+2*clearance+c.FLOOR
    units = ceil(required/c.RACK_UNIT) if units is None else units
    height = panel_height(units)
    if required > height:
        raise TrayFitError('tray height: device_h + 2*clearance + floor exceeds the centred panel height; increase units')
    depth = c.PANEL_THICKNESS+device_d+2*clearance
    if depth > 300:
        raise TrayFitError('device_d and clearance exceed the 300 mm tray print height')
    if min(device_w, device_d) < 40:
        raise TrayFitError('device_w and device_d must be at least 40 mm for the tie slots and webs')
    return dict(units=units, height=height, inner_width=inner, outer_width=outer,
                depth=depth, clearance=clearance)


def _tie_cutter(x, z):
    # Diamond-topped slot: ceiling slopes at 45 degrees in the print frame.
    w, length = c.TIE_WIDTH, c.TIE_LENGTH
    points = [(x-w/2, -1, z-length/2), (x+w/2, -1, z-length/2),
              (x+w/2, -1, z+length/2-w/2), (x, -1, z+length/2),
              (x-w/2, -1, z+length/2-w/2)]
    return extrude(Face(Wire.make_polygon([Vector(*p) for p in points], close=True)),
                   amount=c.FLOOR+2, dir=(0,1,0))


def tray(device_w, device_d, device_h, units=None, clearance=1.0, *, front_cutouts=(), slot_mm=0):
    """Return one solid; optional (x, y, width, height) front windows.

    Coordinates use the panel's physical bottom, not the nominal U boundary.
    Windows must retain a 3 mm frame inside the tray envelope.
    """
    d = tray_dimensions(device_w, device_d, device_h, units, clearance)
    h, depth, inner, outer = d['height'], d['depth'], d['inner_width'], d['outer_width']
    part = panel(d['units'], slot_mm=slot_mm, finished=False)
    part += Pos(0, 0, 0)*Box(outer, c.FLOOR, depth, align=(Align.CENTER, Align.MIN, Align.MIN))
    # The side webs taper from the panel top to a low rear retaining rail.
    # They overlap the panel by its full thickness and the floor by its full height.
    for side in (-1,1):
        x = side*inner/2
        pts = [(x,0,0), (x,h-2,0), (x,h-2,c.PANEL_THICKNESS),
               (x,c.FLOOR+c.RAIL_HEIGHT,depth), (x,0,depth)]
        part += extrude(Face(Wire.make_polygon([Vector(*p) for p in pts], close=True)),
                        amount=c.RAIL_WALL, dir=(side,0,0))
    # 1 mm stress relief along the floor/side junction and front/floor joint.
    roots = []
    for edge in part.edges():
        q = edge.center()
        if ((abs(q.Y-c.FLOOR) < 1e-6 and (
                (abs(abs(q.X)-inner/2) < 1e-6 and q.Z > c.PANEL_THICKNESS) or
                (abs(q.Z-c.PANEL_THICKNESS) < 1e-6 and abs(q.X) < inner/2))) or
                (abs(abs(q.X)-inner/2) < 1e-6 and abs(q.Z-c.PANEL_THICKNESS) < 1e-6
                 and q.Y > c.FLOOR)):
            roots.append(edge)
    part = fillet(roots, 1.0)
    for x in (-device_w/4,device_w/4):
        for z in (c.PANEL_THICKNESS+device_d/3, c.PANEL_THICKNESS+2*device_d/3):
            part -= _tie_cutter(x,z)
    for x,y,w,ht in front_cutouts:
        if not all(isfinite(v) for v in (x,y,w,ht)) or min(w,ht) < 2:
            raise TrayFitError('front cutout must be finite and at least 2 mm wide/high')
        if abs(x)+w/2 > inner/2-3 or y-ht/2 < c.FLOOR+3 or y+ht/2 > h-3:
            raise TrayFitError('front cutout must retain the floor, rails and a 3 mm frame')
        part -= Pos(x,y,-1)*Box(w,ht,c.PANEL_THICKNESS+2,align=(Align.CENTER,Align.CENTER,Align.MIN))
    return finish(part, lambda edge: tie_mating_edge(edge, device_w, device_d))


def tie_mating_edge(edge, device_w, device_d):
    """Functional tie-slot edges: retain the 3 mm aperture and 45-degree roof."""
    q = edge.center()
    return (-1e-6 <= q.Y <= c.FLOOR+1e-6 and any(
        abs(q.X-x) <= c.TIE_WIDTH/2+1e-6 and abs(q.Z-z) <= c.TIE_LENGTH/2+1e-6
        for x in (-device_w/4,device_w/4)
        for z in (c.PANEL_THICKNESS+device_d/3,c.PANEL_THICKNESS+2*device_d/3)))
