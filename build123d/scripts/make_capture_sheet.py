"""Gridfinity capture reference sheet v1 — Letter + A4. Raster PDF at 600 dpi via PIL; ArUco DICT_4X4_50 ids 0-3 clockwise from top-left.
All geometry in mm from the PAGE top-left; constants here are the source of truth.
Run with no arguments to regenerate the public PDFs and both manifest copies.
Tests hash the checked-in PDFs instead: PIL embeds generation timestamps.
"""
import json, hashlib
from pathlib import Path
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
DPI = 600; PX = DPI/25.4
MARKER = 24.0; MARGIN = 8.0; GAP = 4.0; BAR = 100.0
SHEETS = {'letter': (215.9, 279.4), 'a4': (210.0, 297.0)}
FIELD_GRAY = 140  # ~45 % K: white items (+100) and black items (-130) both contrast
def manifest(name):
    W,H = SHEETS[name]
    m = MARGIN; s = MARKER
    markers = {0:[m,m], 1:[W-m-s,m], 2:[W-m-s,H-m-s], 3:[m,H-m-s]}  # top-left corner of each marker, clockwise from TL
    field = [m, m+s+GAP, W-m, H-m-s-GAP]
    bar_y = H-m-s/2
    return {'id': f'{name}-v1', 'page_mm': [W,H], 'dictionary': 'DICT_4X4_50', 'marker_size_mm': s,
            'markers_mm': {str(k): v for k,v in markers.items()}, 'marker_corner_order': 'top-left, top-right, bottom-right, bottom-left (clockwise, page frame)',
            'field_mm': field, 'field_gray_8bit': FIELD_GRAY, 'check_bar_mm': {'x0': round(W/2-BAR/2,2), 'x1': round(W/2+BAR/2,2), 'y': round(bar_y,2), 'length_mm': BAR},
            'origin': 'page top-left, +x right, +y down, millimetres'}
def render(name, out):
    mf = manifest(name); W,H = mf['page_mm']
    img = Image.new('L', (round(W*PX), round(H*PX)), 255)
    d = ImageDraw.Draw(img)
    x0,y0,x1,y1 = mf['field_mm']; d.rectangle([x0*PX, y0*PX, x1*PX, y1*PX], fill=FIELD_GRAY)
    dic = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    spx = round(MARKER*PX)
    for k,(mx,my) in mf['markers_mm'].items():
        mk = cv2.aruco.generateImageMarker(dic, int(k), spx, borderBits=1)
        img.paste(Image.fromarray(mk), (round(mx*PX), round(my*PX)))
    cb = mf['check_bar_mm']; y = cb['y']*PX
    d.line([cb['x0']*PX, y, cb['x1']*PX, y], fill=0, width=round(0.6*PX))
    for x in (cb['x0'], cb['x1']): d.line([x*PX, y-4*PX, x*PX, y+4*PX], fill=0, width=round(0.6*PX))
    for i in range(1,10): d.line([(cb['x0']+10*i)*PX, y-1.5*PX, (cb['x0']+10*i)*PX, y+1.5*PX], fill=0, width=round(0.35*PX))
    try: font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', round(3.2*PX)); small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', round(2.4*PX))
    except Exception: font = small = ImageFont.load_default()
    d.text((W/2*PX, (cb['y']+5.5)*PX), 'Check bar: must measure 100 mm after printing (print at 100 % / actual size, not fit to page)', fill=0, font=small, anchor='mt')
    d.text((W/2*PX, (MARGIN+MARKER/2)*PX), f'Gridfinity capture sheet  {name.upper()} v1', fill=0, font=font, anchor='mm')
    d.text((W/2*PX, (MARGIN+MARKER/2+4.5)*PX), 'Place ONE item fully inside the grey field. Photograph straight down, all four markers visible, no flash.', fill=0, font=small, anchor='mm')
    d.text((W/2*PX, (H-3)*PX), 'stuff.seanoc.com  ·  capture sheet v1', fill=90, font=small, anchor='mb')  # page margin, never inside the field
    pdf = out/f'capture-sheet-{name}-v1.pdf'; png = out/f'capture-sheet-{name}-v1.png'
    img.save(pdf, 'PDF', resolution=DPI); img.resize((round(W*4), round(H*4))).save(png)
    return mf, pdf
if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    out = root/'public/capture'; out.mkdir(parents=True, exist_ok=True)
    ms = {}
    for name in SHEETS:
        mf, pdf = render(name, out); mf['pdf'] = pdf.name; mf['pdf_sha256'] = hashlib.sha256(pdf.read_bytes()).hexdigest(); ms[mf['id']] = mf
        print(name, 'field', mf['field_mm'], 'markers', mf['markers_mm'], 'bar', mf['check_bar_mm'], pdf.stat().st_size, 'bytes')
    manifest_json = json.dumps(ms, indent=2)+'\n'
    (out/'sheets.json').write_text(manifest_json)
    (root/'build123d/capture/sheets.json').write_text(manifest_json)
