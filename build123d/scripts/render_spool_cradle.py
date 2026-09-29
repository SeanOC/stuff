"""Regenerate v2's front/section/75 mm row review sheet and preset STLs.

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
from build123d import Align, Box, Pos
from scripts.export import export_stl
from scripts.thumbnail import _render_view


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
        instance.apply_translation([i*75,0,0])
        rows.append(instance)
    row=trimesh.util.concatenate(rows)
    panels=[('Front (+Y): 70 mm plate',mesh,(0,1,0)),
            ('Side section (+X): arc saddle / closed truss',section_mesh,(1,0,0)),
            ('Three holders: 75 mm cadence / 5 mm plate gaps',row,(1,2,1.2))]
    sheet=Image.new('RGB',(1800,670),'white')
    draw=ImageDraw.Draw(sheet)
    for i,(label,shape,view) in enumerate(panels):
        pixels=_render_view(shape.vertices,shape.faces,shape.vertex_normals,
                           color=np.array([.22,.57,.72]),view_dir=np.array(view,dtype=float),
                           world_up=np.array([0.,0.,1.]),res=600)
        image=Image.fromarray((pixels*255+.5).astype(np.uint8),'RGBA')
        sheet.paste(image,(i*600,40),image)
        draw.text((i*600+12,14),label,fill='black',font_size=18)
    draw.text((12,647),'CAD review / no reference photos. Standing print, Z up. Mount pockets are the only permitted support exception.',fill='black',font_size=17)
    sheet.save(ROOT/'docs/renders/holder_spool_cradle.png')
    for preset in SPEC.presets:
        model=holder(**preset.values)
        export_stl(model,directory/f'holder_spool_cradle_{preset.id}.stl')
        print(f'{preset.id}: {model.volume:.3f} mm^3')


if __name__ == '__main__':
    render()
