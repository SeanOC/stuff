# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# Copyright (c) 2026 Sean O'Connor
"""Little Tikes Dream Machine cartridge and figure tray.

Personal use only; do not sell prints or files. Design/layout ported from
models/littletikes_dream_machine_cartridge_holder.scad at d12a407d64d9.
[C] Dimensions, phase-locked cartridge columns, and auto-fill: source lines
142–239. openGrid snaps: QuackWorks by metasyntactic / openGrid by David D,
consumed through opengrid_snap (CC BY-NC-SA 4.0). openConnect: mitufy's
CC BY 4.0 library port, consumed unchanged through openconnect.grid.

Print back/snaps down (+Y up). Worst load is cartridge weight along the
wall (-Z), with pull-away bending carried by the continuous tray floor.
The figure dome is the approved original FDM overhang; dense snaps leave
short underside bridges, checked at <=10 mm. Library mating edges retain
their published profiles. The SCAD sparse-snaps export-speed hatch is
omitted: its 47.5 mm bridges cannot print support-free.

Continuous analytic roundovers replace the SCAD's 24-layer approximation.
The body is first constructed in the source frame, then rotated to X width,
Y depth, Z wall height, with the figure openings on the upper edge.
The frame is (X, Y, Z) = (width/2-source_X, source_Z, source_Y). The 0.1 mm cutter overlap and 0.02 mm snap embed
are retained for dimensional parity. openConnect alone raises the floor
to at least 5.2 mm for its 2.4 mm backing contract (+0.2 mm by design).
End-open corner pockets narrow by 0.1 mm (within the parity tolerance);
the full holder thereby keeps a >=0.9 mm outer-corner wall. No independent mount geometry or shims.
"""
from dataclasses import replace
import math

from build123d import (Align, Axis, Box, Circle, Pos, Rectangle,
                       RectangleRounded, Rot, Plane, chamfer, extrude, fillet, loft)
from holders.registry import ModelSpec, Param, Preset, register
from openconnect.constants import TILE_SIZE
from openconnect.grid import fixtures, layout
from openconnect.slot import pocket_depth
from opengrid_snap import snap
from opengrid_snap.constants import LITE_HEIGHT, FULL_EXTRA, CORE_WIDTH, NUB_DEPTH

PITCH = TILE_SIZE  # [C] source :187; the shared library cell pitch
WELD = .02  # [C] source :191; library top plate is embedded, never shimmed
MOUNT = 'openconnect-slot'


def dimensions(values=None):
    p = SPEC.resolve_values(values)
    if p['mount_type'] == 'openconnect':
        # rev 7: preserve 2.4 mm backing below the 0.1 mm pocket overlap.
        p['floor_z'] = max(p['floor_z'], pocket_depth() + 2.4 + .1)
    p['width'] = PITCH*p['grid_cols']
    p['height'] = PITCH*p['grid_rows']
    p['lift'] = (LITE_HEIGHT + (0 if p['snap_lite'] else FULL_EXTRA) - WELD
                 if p['mount_type'] == 'opengrid' else 0)
    return p


def placements(values=None):
    p = dimensions(values)
    return [replace(s, z=s.z+p['height']/2)
            for s in layout(p['grid_cols'], p['grid_rows'], lock='corners')]


def mount_for_values(values):
    return MOUNT if values['mount_type'] == 'openconnect' else None


def mount_fixtures(mount_type, values):
    if mount_type != MOUNT:
        raise ValueError(f'unsupported mount: {mount_type}')
    p = dimensions(values)
    return fixtures(placements(values)) if mount_for_values(p) else None


def _cartridge_tools(width, p):
    """Core and analytic rim cutters sharing exactly the same fit profile."""
    sw, sl = width, p['slot_l']
    d, R = p['body_h'], p['top_round']
    profile = (RectangleRounded(sw, sl, p['slot_corner_r'])
               if p['slot_corner_r'] else Rectangle(sw, sl))
    bottom = max(p['floor_z'], d-p['slot_depth'])-.1
    pocket = Pos(0,0,bottom)*extrude(profile, amount=d-bottom+.1)
    rim = None
    if R:
        blank = Box(sw+2*R+4,sl+2*R+4,R+2,
                    align=(Align.CENTER,Align.CENTER,Align.MIN))
        carrier = blank-Pos(0,0,-1)*extrude(profile,amount=R+4)
        edges = [e for e in carrier.edges() if abs(e.center().Z-(R+2))<1e-6
                 and abs(e.center().X)<sw/2+1e-6 and abs(e.center().Y)<sl/2+1e-6]
        carrier = fillet(edges,R)
        rim = Pos(0,0,d-R-2)*(blank-carrier)
    return pocket, rim


def _body(p):
    w,h,d,R=p['width'],p['height'],p['body_h'],p['top_round']
    part=Pos(w/2,h/2,0)*extrude(RectangleRounded(w,h,p['body_corner_r']),amount=d)
    part = chamfer(part.edges().group_by(Axis.Z)[0], .4)
    if R: outer_tool=part-fillet(part.edges().group_by(Axis.Z)[-1],R)
    sw,sl=p['slot_w'],p['slot_l']
    bottom=max(p['floor_z'],d-p['slot_depth'])-.1
    nc=max(0,math.floor((w-sw)/p['slot_col_pitch'])+1)
    nr=max(0,math.floor((h-p['fig_depth']-2-sl)/p['slot_row_pitch'])+1)
    module = 2*PITCH
    x0=PITCH+module*math.floor(((w-(nc-1)*p['slot_col_pitch'])/2-PITCH)/module+.5)
    y0=(h-p['fig_depth']-2-(nr-1)*p['slot_row_pitch'])/2
    tools = {}
    pockets = []
    for i in range(nc):
        for j in range(nr):
            xc, yc = x0+i*p['slot_col_pitch'], y0+j*p['slot_row_pitch']
            end_open = yc-sl/2 <= 1e-6 or yc+sl/2 >= h-1e-6
            margin = min(xc-sw/2,w-xc-sw/2)
            near_corner = 1e-6 < margin < p['body_corner_r']
            # The full holder's end-open first pocket meets a rounded outer
            # corner. A 0.1 mm narrower fit (the source parity tolerance)
            # keeps that corner wall >=0.9 mm, without moving its grid centre.
            width = sw-.1 if end_open and near_corner else sw
            if width not in tools:
                tools[width] = _cartridge_tools(width,p)
            pockets.append((Pos(xc,yc,0),width))
    if pockets:
        part = part.cut(*[loc*tools[width][0] for loc,width in pockets])
    profile=Pos(0,p['fig_rect_h']/2)*Rectangle(p['fig_w'],p['fig_rect_h'])+Pos(0,p['fig_rect_h'])*Circle(p['fig_w']/2)
    profile=profile & (Pos(0,250)*Rectangle(1000,500))
    nf=max(0,math.floor((w-p['fig_w'])/p['fig_pitch'])+1)
    fx=(w-(nf-1)*p['fig_pitch'])/2
    figure=Rot(90,0,0)*extrude(profile,amount=p['fig_depth']+.1)
    part=part.cut(*[Pos(fx+i*p['fig_pitch'],h+.1,p['floor_z'])*figure for i in range(nf)])
    # Ease the user-facing figure openings; preserve the internal fit profile.
    front = [e for e in part.edges() if abs(e.bounding_box().min.Y-h)<1e-6
             and abs(e.bounding_box().max.Y-h)<1e-6
             and e.bounding_box().min.Z >= p['floor_z']-1e-6
             and e.bounding_box().max.Z < d-R-1e-6]
    if front:
        # Preserve the source mouth footprint within 0.1 mm overall.
        part = chamfer(front, .04)
    # Full-width slots break through a side. Use a tiny lofted lead-in at
    # that opening: OCC edge chamfering fails where it meets the top fillet.
    # 0.04 mm per side stays within the 0.1 mm pocket-footprint parity budget.
    for i in range(nc):
        xc = x0+i*p['slot_col_pitch']
        for side, sign in ((0, 1), (w, -1)):
            if not xc-sw/2-1e-6 <= side <= xc+sw/2+1e-6:
                continue
            for j in range(nr):
                yc = y0+j*p['slot_row_pitch']
                zc = (bottom+d+2)/2
                inner = Plane(origin=(side+sign*.04,yc,zc),
                              x_dir=(0,1,0), z_dir=(1,0,0))*Rectangle(sl,d+2-bottom)
                outer = Plane(origin=(side-sign*.001,yc,zc),
                              x_dir=(0,1,0), z_dir=(1,0,0))*Rectangle(sl+.08,d+2-bottom+.08)
                part = part-loft([inner,outer])
    # End-open rows intersect the outer rounded corners. Finish their
    # exposed edges BEFORE the top roundovers; afterwards OCC cannot
    # chamfer the tiny edge where the two curved surfaces meet.
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    exposed = []
    for edge, faces in adjacency.items():
        if len(faces) != 2:
            continue
        point = edge.center()
        if abs(point.Z-d) < 1e-6:
            continue
        n0, n1 = [f.normal_at(point) for f in faces]
        if n0.dot(n1) < 1e-6 and not part.is_inside(point+(n0-n1)*.005):
            exposed.append(edge)
    if exposed:
        part = chamfer(exposed,.04)
    if R:
        part = part-outer_tool
        part = part.cut(*[loc*tools[width][1] for loc,width in pockets])
    return part


class _DomeSurface:
    """Exact thin cylindrical envelope of one approved figure dome.

    Analytic membership avoids repeated OCCT classification in the audit;
    it does not exempt the rectangular pocket, floor or neighbouring wall.
    """
    def __init__(self, x, y, radius, depth, height):
        self.x, self.y, self.radius, self.depth, self.height = x, y, radius, depth, height

    def is_inside(self, point, tolerance=1e-6):
        x, y, z = point
        return (self.height-self.depth-tolerance <= z <= self.height + tolerance
                and abs(math.hypot(x-self.x, y-self.y)-self.radius)
                <= .001+tolerance)


def audit_exclusions(values=None, *, underside=True):
    """Only approved dome surfaces, library snaps, and the dense bridge face.

    Tests independently enumerate the raw failing faces and measure the
    underside span before excluding that plane. No wall-sized padding.
    """
    p = dimensions(values)
    w, h, lift = p['width'], p['height'], p['lift']
    nf = max(0, math.floor((w-p['fig_w'])/p['fig_pitch'])+1)
    x0 = -(nf-1)*p['fig_pitch']/2
    snap_half = CORE_WIDTH/2 + NUB_DEPTH + .001
    regions = [_DomeSurface(x0+i*p['fig_pitch'],
                           lift+p['floor_z']+p['fig_rect_h'],
                           p['fig_w']/2, p['fig_depth'], h) for i in range(nf)]
    if p['mount_type'] == 'opengrid':
        # These envelopes end at the body interface. Every face below it
        # comes from the unchanged library snap (test_opengrid_snap inventory).
        for i in range(p['grid_cols']):
            for j in range(p['grid_rows']):
                x, z = (i+.5)*PITCH-w/2, (j+.5)*PITCH
                regions.append((x-snap_half, -.001, z-snap_half,
                                x+snap_half, lift+.001, z+snap_half))
        if underside:
            regions.append((-w/2, lift-.001, 0, w/2, lift+.001, h))
    return regions


def build(values=None):
    p = dimensions(values)
    part = Pos(0, 0, p['lift'])*_body(p)
    if p['mount_type'] == 'opengrid':
        connector = snap(lite=p['snap_lite'], directional=False)
        part = part.fuse(*[Pos((i+.5)*PITCH, (j+.5)*PITCH, 0)*connector
                          for i in range(p['grid_cols'])
                          for j in range(p['grid_rows'])])
    part = Pos(p['width']/2, 0, 0)*Rot(0, 0, 180)*Rot(90, 0, 0)*part
    if p['mount_type'] == 'openconnect':
        part = part.cut(*mount_fixtures(MOUNT, values).cutters)
    return part


SPEC = register(ModelSpec(
    name='littletikes_dream_machine_cartridge_holder',
    build=build,
    title='Little Tikes Dream Machine cartridge + figure holder',
    description='Wall-mounted tray with auto-filled 52x14 mm cartridge slots and rounded figure pockets. Choose dense openGrid snaps, a blank back, or openConnect receivers on the 28 mm grid.',
    category_id='toys',
    mounts=(MOUNT,),
    mount_for_values=mount_for_values,
    print_orientation=(0., 1., 0.),
    params=(
        Param('mount_type', 'enum', "opengrid", group='mount', label='Back-face mount', choices=('opengrid', 'blank', 'openconnect'), filename=True),
        Param('grid_cols', 'integer', 2, min=2, max=9, step=1, group='grid', label='Width (28mm openGrid cells)'),
        Param('grid_rows', 'integer', 4, min=3, max=9, step=1, group='grid', label='Height (28mm openGrid cells)'),
        Param('snap_lite', 'boolean', True, group='grid', label='Lite snaps (3.4mm not 6.8mm; openGrid mount)'),
        Param('body_h', 'number', 41, min=38, max=55, step=1, group='grid', unit='mm', label='Body depth out from the wall'),
        Param('body_corner_r', 'number', 3, min=0.5, max=8, step=0.5, group='grid', unit='mm', label='Body outer-corner radius'),
        Param('slot_w', 'number', 52, min=30, max=56, step=0.5, group='cartridge', unit='mm', label='Cartridge slot width'),
        Param('slot_l', 'number', 14, min=8, max=19, step=0.5, group='cartridge', unit='mm', label='Cartridge slot length'),
        Param('slot_depth', 'number', 36, min=10, max=40, step=1, group='cartridge', unit='mm', label='Cartridge slot depth'),
        Param('floor_z', 'number', 5, min=2, max=8, step=0.5, group='cartridge', unit='mm', label='Pocket floor height above the back'),
        Param('slot_col_pitch', 'number', 56, min=54, max=90, step=0.5, group='cartridge', unit='mm', label='Slot column pitch (X; default 56 = 2 openGrid cells)'),
        Param('slot_row_pitch', 'number', 22, min=18, max=40, step=0.5, group='cartridge', unit='mm', label='Cartridge row pitch'),
        Param('slot_corner_r', 'number', 0, min=0, max=6, step=0.5, group='cartridge', unit='mm', label='Slot interior corner radius (0 = square)'),
        Param('top_round', 'number', 1.2, min=0, max=3, step=0.2, group='cartridge', unit='mm', label='Top-edge round-over (outer rim + slot rims; 0=off)'),
        Param('fig_w', 'number', 43.5, min=24, max=46, step=0.5, group='figures', unit='mm', label='Figure pocket width (dome dia.)'),
        Param('fig_rect_h', 'number', 9, min=3, max=13, step=0.5, group='figures', unit='mm', label='Figure straight-wall height'),
        Param('fig_depth', 'number', 10, min=5, max=18, step=0.5, group='figures', unit='mm', label='Figure pocket depth into front'),
        Param('fig_pitch', 'number', 49.25, min=47, max=90, step=0.25, group='figures', unit='mm', label='Figure pocket pitch (X)'),
    ),
    presets=(
        Preset('default', 'Default (2x4 tile, openGrid snaps)', {}),
        Preset('full_holder', 'Full holder (9x8 cells)', {'grid_cols': 9, 'grid_rows': 8}),
        Preset('blank_back', 'Blank back (no connector features)', {'mount_type': 'blank'}),
        Preset('openconnect', 'openConnect receivers (2x4 tile)', {'mount_type': 'openconnect'}),
    ),
))
