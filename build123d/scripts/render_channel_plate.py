"""Render the unregistered channel demo and an X=12.5 longitudinal section.

Run: uv run --project build123d python build123d/scripts/render_channel_plate.py
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw
from build123d import Align, Box, Pos

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from multibuild import demo_plate as demo
from scripts.export import export_stl
from scripts.thumbnail import _render_view
from tests.print_audit import audit


def render():
    plate = demo.channel_plate()
    section = plate & (Pos(12.5, -1, -1) * Box(50, 10, 102, align=(Align.MIN, Align.MIN, Align.MIN)))
    panels = [('Mount face (-Y): entries Z=12.5 / 37.5', plate, (0,-1,0)),
              ('Section X=12.5: entry, channel and closed top', section, (-1,-.15,.05))]
    sheet = Image.new('RGB', (1200,670), 'white')
    draw = ImageDraw.Draw(sheet)
    with tempfile.TemporaryDirectory() as directory:
        for i, (label, part, view) in enumerate(panels):
            path = Path(directory)/f'{i}.stl'
            export_stl(part, path)
            mesh = trimesh.load_mesh(path)
            mesh = trimesh.graph.smooth_shade(mesh, angle=np.radians(35))
            pixels = _render_view(mesh.vertices, mesh.faces, mesh.vertex_normals,
                                  color=np.array([.22,.57,.72]), view_dir=np.array(view),
                                  world_up=np.array([0.,0.,1.]), res=600)
            image = Image.fromarray((pixels*255+.5).astype(np.uint8), 'RGBA')
            sheet.paste(image, (i*600,40), image)
            draw.text((i*600+12,14), label, fill='black', font_size=18)
    draw.text((12,647), '70 x 100 x 7 mm / standing +Z / library pockets use the existing support exception', fill='black', font_size=17)
    sheet.save(ROOT/'docs/renders/channel_plate.png')
    print(f'channel demo: N/A -> {plate.volume:.3f} mm^3')
    print(f'slot demo: 44255.325 -> {demo.build().volume:.3f} mm^3')
    fx = demo.mount_fixtures(demo.CHANNEL_MOUNT,{})
    print(audit(plate,demo.PRINT_ORIENTATION,cutters=fx.cutters).format())


if __name__ == '__main__':
    render()
