# SPDX-License-Identifier: CC-BY-SA-4.0
"""Printed drawer stopper clips, adapted under CC BY-SA 4.0.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:1363-1368
(placement) and :1807-1837 (drawer_stopper). The clip is a flange, a shaft
through the shell wall and two snap legs with wedge nubs. Every feature is a
prism along the source's stopper-height axis, so the clip is one 2D profile
extruded 2.0 mm. hole_excess applies only to holes (:1820), so the author's
pair is two identical clips 28 mm apart.

Print frame = model frame: flat on the bed, profile in XY, 2.0 mm tall;
clip length along -Y from the flange face at Y=0. A clip pushed through a
shell stopper hole stops the container's rear lip; its legs load in shear
across the layers, the nubs carry only the snap retention.

Exception register (§8, bed-contact chamfer, design-guidelines §1):
| Family | Reason / measured | Authority / regression |
| Z=0 profile boundary of both clips (every edge of the extrusion's bottom face, found by adjacency to it) | Kept sharp as in stoppers.stl (bbox 34.4 x 8.3 x 2.0, [C] :1807-1837 has no bed treatment); a 0.3 mm relief leaves a 0.1 mm land on the 0.7 mm flange and removes the 0.6 mm nubs' first layer; print_audit bed_chamfer = absent at L 4/6/12. Elephant foot is left to the slicer's first-layer compensation (0.1-0.15 mm) | Mayor, pst-t0ob3.4, 2026-10-14; test_stopper_bed_edge_exception_is_exactly_the_profile_boundary, test_bed_chamfer_exception_does_not_reach_other_parts |
"""
from math import sqrt

from build123d import Face, Line, Pos, Solid, ThreePointArc, Wire

from openconnect.constants import TILE_SIZE
from . import constants as c

LEG_THICKNESS = 1.6  # [C] :1808
LENGTH_CLEARANCE = 0.1  # [C] :1814 stopper_clip_length_clearance


def dimensions(values=None):
    """Clearance-reduced sizes ([C] :1808-1814) for one clip."""
    v = values or {}
    length = v.get('stopper_clip_length', 6)
    wall = v.get('shell_thickness', 2.4)
    width = c.STOPPER_WIDTH - 2*c.STOPPER_WIDTH_CLEARANCE
    height = c.STOPPER_HEIGHT - 2*c.STOPPER_HEIGHT_CLEARANCE
    slot = c.STOPPER_WIDTH - 2*LEG_THICKNESS - 2*c.STOPPER_WIDTH_CLEARANCE
    outer = min(c.STOPPER_ROUNDING, min(width, length)/2)
    inner = min(c.STOPPER_ROUNDING, min(slot, length)/2)
    nub_length = min(3, length - outer)
    return dict(length=length, height=height, width=width, slot=slot,
                flange_width=c.STOPPER_WIDTH + c.STOPPER_FLANK_WIDTH - 2*c.STOPPER_WIDTH_CLEARANCE,
                flange_depth=c.STOPPER_FLANK_DEPTH - LENGTH_CLEARANCE,
                shaft=wall - c.STOPPER_FLANK_DEPTH, outer=outer, inner=inner,
                nub_length=nub_length, nub_width=min(.6, nub_length))


def _arc(start, end, centre):
    """Quarter arc about ``centre`` (its midpoint lies on the bisector)."""
    (sx, sy), (ex, ey), (cx, cy) = start, end, centre
    r = sqrt((sx-cx)**2+(sy-cy)**2)
    mx, my = (sx+ex)/2-cx, (sy+ey)/2-cy
    k = r/sqrt(mx*mx+my*my)
    return ThreePointArc((sx, sy, 0), (cx+mx*k, cy+my*k, 0), (ex, ey, 0))


def profile(values=None):
    """Right half (X >= 0) outline, mirrored; returns the closed Face."""
    d = dimensions(values)
    hw, fw, sw = d['width']/2, d['flange_width']/2, d['slot']/2
    y1 = -d['flange_depth']            # flange underside / shaft top
    y2 = y1-d['shaft']                 # shaft end / leg root
    y3 = y2-d['length']                # leg tips
    r, ro, ri = c.STOPPER_ROUNDING, d['outer'], d['inner']
    nl, nw = d['nub_length'], d['nub_width']
    # Concave flare under the flange (rounding=-0.4, :1817), the nub with its
    # square face toward the flange (align=TOP, :1830), rounded leg tips
    # (:1823 outer, :1827 inner) and the rounded slot end (:1825).
    right = [('line', (0, 0), (fw, 0)), ('line', (fw, 0), (fw, y1)),
             ('line', (fw, y1), (hw+r, y1)), ('arc', (hw+r, y1), (hw, y1-r), (hw+r, y1-r)),
             ('line', (hw, y1-r), (hw, y2)), ('line', (hw, y2), (hw+nw, y2)),
             ('line', (hw+nw, y2), (hw, y2-nl)), ('line', (hw, y2-nl), (hw, y3+ro)),
             ('arc', (hw, y3+ro), (hw-ro, y3), (hw-ro, y3+ro)),
             ('line', (hw-ro, y3), (sw+ri, y3)),
             ('arc', (sw+ri, y3), (sw, y3+ri), (sw+ri, y3+ri)),
             ('line', (sw, y3+ri), (sw, y2-ri)),
             ('arc', (sw, y2-ri), (sw-ri, y2), (sw-ri, y2-ri)),
             ('line', (sw-ri, y2), (0, y2))]
    right = [s for s in right if s[0] == 'arc' or s[1] != s[2]]

    def mirror(seg):
        flip = [(-x, y) for x, y in seg[1:]]
        return (seg[0], flip[1], flip[0], *flip[2:])
    segments = right+[mirror(s) for s in reversed(right)]
    edges = [Line((*s[1], 0), (*s[2], 0)) if s[0] == 'line' else _arc(*s[1:])
             for s in segments]
    return Face(Wire(edges))


def build(values=None):
    """The author's pair ([C] :1363-1368): two clips, 28 mm apart, flat."""
    clip = Solid.extrude(profile(values), (0, 0, dimensions(values)['height']))
    return (clip+Pos(TILE_SIZE, 0, 0)*clip).clean()


def audit_exclusions(values=None):
    """Exact envelopes of the author's sub-0.9 mm snap features.

    The 0.7 mm flange (flank depth 0.8 - 0.1 clearance) seats in the
    shell's 0.8 mm flange recess and the 0.6 mm wedge nubs ([C] :1812) are
    the snap; both are mating dimensions of the shell's stopper hole.
    Mayor-approved exception row (pst-t0ob3.4 Q2, 2026-10-14); the
    envelope bound is enforced in tests/test_openconnect_dividers.py.
    """
    from build123d import Box
    d = dimensions(values)
    regions = []
    for x0 in (0, TILE_SIZE):
        regions.append(Pos(x0, -d['flange_depth']/2, d['height']/2)*Box(
            d['flange_width']+.002, d['flange_depth']+.002, d['height']+.002))
        r = c.STOPPER_ROUNDING
        for side in (-1, 1):  # the flare quarter-rounds under the flange
            regions.append(Pos(x0+side*(d['width']/2+r/2), -d['flange_depth']-r/2, d['height']/2)
                           * Box(r+.002, r+.002, d['height']+.002))
        for side in (-1, 1):
            x = x0+side*(d['width']/2+d['nub_width']/2)
            y = -d['flange_depth']-d['shaft']-d['nub_length']/2
            regions.append(Pos(x, y, d['height']/2)*Box(
                d['nub_width']+.002, d['nub_length']+.002, d['height']+.002))
    return regions
