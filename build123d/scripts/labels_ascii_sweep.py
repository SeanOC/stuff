"""Labels spike (pst-0zfra): stroke/gap of every printable ASCII glyph at 10 pt.

Run from build123d/: PYTHONPATH=. uv run python scripts/labels_ascii_sweep.py
"""
import time
from labels.label_text import text_sketch, stroke_and_gap
t0 = time.perf_counter(); rows = []
for code in range(0x21, 0x7f):
    ch = chr(code); st, gp = stroke_and_gap(text_sketch(ch)); rows.append((st, gp, ch))
print(f'elapsed {time.perf_counter()-t0:.1f}s, {len(rows)} glyphs')
print('cap height H at size 10:', round(text_sketch('H').bounding_box().size.Y, 3))
print('thinnest strokes:', [(c, round(s, 2)) for s, g, c in sorted(rows)[:12]])
print('narrowest gaps:', [(c, round(g, 2)) for g, s, c in sorted((g, s, c) for s, g, c in rows)[:12]])
alnum = [r for r in rows if r[2].isalnum()]
print('alnum min stroke', min(alnum), 'min gap', min(alnum, key=lambda r: r[1]))
