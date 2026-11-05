"""Mayor-approved openGrid retention-waist exception, 2026-11-05.

Only the exposed 0.8 mm wall prisms inside the vendor cutter's planar waist
band qualify. Neither the taper, corner walls nor backing is excluded. Check
the complete prism is still solid before skipping its wall samples; damage
inside the approved region must not disappear behind the exception.
"""
from dataclasses import replace
from functools import lru_cache

from build123d import Align, Box, Plane, Pos, Rot, chamfer
from opengrid.base import BaseSnapSlotCutter, ConnectorCutter
from opengrid_tile.tile import FULL, LITE, PITCH, RELIEF, cells, outline, outline_solid
from tests import print_audit as a


@lru_cache(maxsize=1)
def reference_waist():
    opening = BaseSnapSlotCutter()
    width = opening.snap_cut_bottom_dent_width
    assert abs(width - 0.8) < 1e-9, 'approved vendor retention dimension drifted'
    low = FULL/2 - opening.snap_cut_bottom_dent_height
    high = FULL - low
    faces = [f for f in opening.faces()
             if abs(f.bounding_box().min.Z-low) < 1e-7
             and abs(f.bounding_box().max.Z-high) < 1e-7
             and abs(f.normal_at().Z) < 1e-7]
    assert len(faces) == 4
    # Pin all four geometric members; no selection by measured thinness.
    for f in faces:
        b = f.bounding_box()
        assert min(b.size.X, b.size.Y) < 1e-7
        assert abs(max(b.size.X, b.size.Y)-13.84608947566) < 1e-7
    return width, low, high, max(f.bounding_box().size.Y for f in faces)/2


def waist_boxes(values):
    width, low, high, span = reference_waist()
    kept = cells(values['x_count'], values['y_count'], values['omit_cells'])
    height = LITE if values['style'] == 'lite' else FULL
    total = height + values['backing_mm']
    z0, z1 = total-min(height, high), total-low
    boxes = []
    for x, y in sorted(kept):
        cx, cy = (x-(values['x_count']-1)/2)*PITCH, (y-(values['y_count']-1)/2)*PITCH
        for dx, dy in ((-1,0), (1,0), (0,-1), (0,1)):
            if (x+dx, y+dy) in kept:
                continue
            if dx:
                end = cx + dx*PITCH/2
                boxes.append((min(end, end-dx*width), cy-span, z0,
                              max(end, end-dx*width), cy+span, z1))
            else:
                end = cy + dy*PITCH/2
                boxes.append((cx-span, min(end, end-dy*width), z0,
                              cx+span, max(end, end-dy*width), z1))
    return boxes


def connector_envelopes(values):
    """Exact vendor cutters, clipped to tile depth; only overhang classification.

    Library mating cutters are excluded from angle checks by the existing
    print-audit policy. Keep the raw bridge measurement (5 mm for these pockets)
    and wall checks, including backing, without exclusions.
    """
    nx, ny = values['x_count'], values['y_count']
    if len(cells(nx,ny,values['omit_cells'])) != nx*ny:
        return []
    w, d = nx*PITCH, ny*PITCH
    height = LITE if values['style']=='lite' else FULL
    slab = Box(w,d,height,align=(Align.CENTER,Align.CENTER,Align.MIN))
    cutter = ConnectorCutter()
    regions = []
    for count, edges in (
        (nx, [('neg_y',-d/2,0),('pos_y',d/2,180)]),
        (ny, [('neg_x',-w/2,-90),('pos_x',w/2,90)]),
    ):
        for edge, outside, angle in edges:
            if not values['connector_'+edge]:
                continue
            for i in range(count-1):
                along = (i-(count-2)/2)*PITCH
                x,y = (along,outside) if edge.endswith('y') else (outside,along)
                region = (Pos(x,y,FULL/2)*Rot(0,0,angle)*cutter) & slab
                regions.append(region.mirror(Plane.XY.offset((height+values['backing_mm'])/2)))
    return regions


def accepted_report(part, values, raw):
    """Keep raw measurements; accept only the waist and library connector angles."""
    regions = waist_boxes(values)
    # The mayor also requires outer bed relief on bare Lite tiles. Their back
    # ends in the waist, so compare those prisms to vendor MINUS exactly that
    # prescribed relief. The unrelieved 0.8 mm datum remains above Z=0.3.
    relief_envelope = None
    if values['style']=='lite' and values['backing_mm']==0:
        profile = outline(values['x_count'],values['y_count'],values['omit_cells'])
        envelope = outline_solid(profile,LITE)
        edges = [e for e in envelope.edges() if abs(e.bounding_box().max.Z)<1e-6]
        relief_envelope = chamfer(edges,length=RELIEF)
    for x0, y0, z0, x1, y1, z1 in regions:
        reference = Pos(x0,y0,z0)*Box(x1-x0, y1-y0, z1-z0, align=(Align.MIN,)*3)
        if relief_envelope is not None:
            reference &= relief_envelope
        missing = reference - part
        assert missing is None or abs(missing.volume) < 1e-6, 'damaged retention waist'
    # Only library connector angles may be exempted; raw local bridge spans,
    # fillets and all wall measurements outside the waist remain blocking.
    boxes = [tuple(v + (-1e-6 if i < 3 else 1e-6) for i, v in enumerate(b)) for b in regions]
    remainder = a._min_wall(a._ClassifiedPart(part), (0,0,1), boxes)
    connectors = [a._ExactExclusion(c) for c in connector_envelopes(values)]
    overhang = a._max_overhang(a._ClassifiedPart(part), (0,0,1), connectors, 0)
    return replace(raw, min_wall_mm=round(remainder, 3),
                   max_overhang_deg=round(overhang,1)), len(regions)
