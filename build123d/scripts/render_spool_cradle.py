"""Regenerate v2.1 placement-aid views, 75 mm row, preset STLs, the
openConnect preset's review sheet and the points preset's back view.

Run from the repo root:
  uv run --project build123d python build123d/scripts/render_spool_cradle.py
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from holders.spool_cradle import SPEC, holder, dimensions
from multibuild import fixpoint as fp
from build123d import Align, Box, Pos, export_gltf
from scripts.export import export_stl, section_svg
from scripts.thumbnail import ReviewContext, _render_view, render_review

REVIEW_PRESET='bambu_reusable_200_openconnect'
POINTS_PRESET='bambu_reusable_200_points'


def render():
    directory=ROOT/'docs/exports'
    directory.mkdir(exist_ok=True)
    part=holder()
    path=directory/'holder_spool_cradle.stl'
    export_stl(part,path)
    mesh=trimesh.load_mesh(path)
    p=dimensions()
    # Cut through the near flange web so the panel cannot obscure its truss.
    cut=Pos(p['rail_inner']+1.2, -1, -1)*Box(100,400,400,
        align=(Align.MIN,Align.MIN,Align.MIN))
    section_part=part-cut
    section_path=directory/'holder_spool_cradle_section.stl'
    export_stl(section_part,section_path)
    section_mesh=trimesh.load_mesh(section_path)
    section_path.unlink()
    rows=[]
    for i in range(3):
        instance=mesh.copy()
        instance.apply_translation([i*p['cadence'],0,0])
        rows.append(instance)
    row=trimesh.util.concatenate(rows)
    panels=[('Front (+Y): widened rails and lead-in guides',mesh,(0,1,0)),
            ('Side section (+X): arc saddle / closed truss',section_mesh,(1,0,0)),
            ('Three holders: 75 mm cadence / 1 mm guide gaps',row,(1,2,1.2)),
            ('End view (-X): saddle and side guide',mesh,(-1,0,0))]
    sheet=Image.new('RGB',(1400,1510),'white')
    draw=ImageDraw.Draw(sheet)
    for i,(label,shape,view) in enumerate(panels):
        pixels=_render_view(shape.vertices,shape.faces,shape.vertex_normals,
                           color=np.array([.22,.57,.72]),view_dir=np.array(view,dtype=float),
                           world_up=np.array([0.,0.,1.]),res=700)
        image=Image.fromarray((pixels*255+.5).astype(np.uint8),'RGBA')
        x, y = (i%2)*700, (i//2)*740
        sheet.paste(image,(x,y+40),image)
        draw.text((x+12,y+14),label,fill='black',font_size=18)
    draw.text((12,1487),'CAD review / no reference photos. Standing print, Z up. Mount pockets are the only permitted support exception.',fill='black',font_size=17)
    sheet.save(ROOT/'docs/renders/holder_spool_cradle.png')
    for preset in SPEC.presets:
        model=holder(**preset.values)
        export_stl(model,directory/f'holder_spool_cradle_{preset.id}.stl')
        print(f'{preset.id}: {model.volume:.3f} mm^3')
        if preset.id == REVIEW_PRESET:
            review(model)
        if preset.id == POINTS_PRESET:
            points_back(model,preset.values)


def review(model):
    """Five-tile review sheet and analytic section for the openConnect preset."""
    renders=ROOT/'docs/renders'
    glb=ROOT/'out/holder_spool_cradle_openconnect.glb'
    glb.parent.mkdir(exist_ok=True)
    export_gltf(model,str(glb),binary=True)
    ctx=ReviewContext(f'{SPEC.slug}-openconnect',SPEC.print_orientation,
                      SPEC.review_sections,('openconnect-slot',))
    render_review(glb,renders/'review'/f'{ctx.slug}.png',ctx=ctx)
    (renders/'sections'/f'{ctx.slug}.svg').write_text(
        section_svg(model,ctx.sections[0]),encoding='utf-8')


def points_back(model,values):
    """Back (board-facing) view of the four Fix Point slots, lip end up."""
    p=dimensions(values)
    seat=p['point_seats'][1]
    up=lambda lo,hi: Box(hi[0]-lo[0],hi[1]-lo[1],hi[2]-lo[2],align=(Align.MIN,)*3)
    plate=model&(Pos(-40,-1,-1)*up((0,0,0),(80,p['plate_thickness']+1,p['plate_height']+2)))
    # Cut on the right column's axis: the lip profile at the top of the slot.
    cut=model&(Pos(0,-1,seat-fp.SLOT_LENGTH)*up((0,0,0),(12.5,p['plate_thickness']+1,fp.SLOT_LENGTH+12)))
    directory=ROOT/'docs/exports'
    from holders.spool_cradle import FP_MOUNT, mount_fixtures
    boxes=[c.bounding_box() for c in mount_fixtures(FP_MOUNT,values).cutters]
    panels=[('Back (-Y): four Fix Point slots (orange), 25 x 50 mm',model,(.25,-1,.2)),
            ('Plate close-up: wells below, octagon lips above',plate,(.3,-1,.35)),
            ('Cut at x = 12.5 (+X): lip end up, well below',cut,(1,-.25,0))]
    sheet=Image.new('RGB',(2100,780),'white')
    draw=ImageDraw.Draw(sheet)
    for i,(label,shape,view) in enumerate(panels):
        path=directory/'_points_back.stl'
        export_stl(shape,path)
        mesh=trimesh.load_mesh(path)
        path.unlink()
        mesh.unmerge_vertices()  # flat shading: crisp pocket edges
        # Pocket faces orange: triangle centroids inside a slot cutter, off the back face.
        c=mesh.triangles_center
        pocket=np.zeros(len(c),bool)
        for b in boxes:
            pocket|=((c[:,0]>=b.min.X-1e-3)&(c[:,0]<=b.max.X+1e-3)&(c[:,1]>.02)&(c[:,1]<=b.max.Y+1e-3)
                     &(c[:,2]>=b.min.Z-1e-3)&(c[:,2]<=b.max.Z+1e-3))
        colors=np.where(pocket[:,None],[.93,.55,.18],[.22,.57,.72])
        pixels=_render_view(mesh.vertices,mesh.faces,mesh.vertex_normals,face_colors=colors,
                           color=np.array([.22,.57,.72]),view_dir=np.array(view,dtype=float),
                           world_up=np.array([0.,0.,1.]),res=700)
        image=Image.fromarray((pixels*255+.5).astype(np.uint8),'RGBA')
        sheet.paste(image,(i*700,40),image)
        draw.text((i*700+12,14),label,fill='black',font_size=18)
    draw.text((12,752),'Z up (standing print). Lowering the holder onto board Fix Points carries each head up from its well and under its lip.',
              fill='black',font_size=17)
    sheet.save(ROOT/'docs/renders/holder_spool_cradle_points_back.png')


if __name__ == '__main__':
    render()
