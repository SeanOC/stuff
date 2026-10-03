"""Shared label numbers (labels epic pst-mbh56; DECISIONS in docs/labels-spike.md).

One card envelope in v1 (D7, mayor call): the label_card model (L2) and the
spool cradle's label holder (L3) both size from these, so the card always
fits the holder it is made for. All lengths in mm.
"""

# D7 card envelope: holder_spool_cradle's default panel width (66) - 6.
CARD_W = 60.0
CARD_H = 20.0
CARD_T = 1.6
CORNER_R = 1.5
EDGE_CHAMFER = 0.4      # both faces: bed edge (elephant's foot) and the top rim
TEXT_MARGIN = 2.0       # ink to card edge on every side; covers the holder lip

# Card size choices (label_card's `size` param) -> (width, height).
CARD_SIZES = {'spool-cradle': (CARD_W, CARD_H)}

INLAY_DEPTH = 0.6       # D9: 3 layers at 0.2; also the raised-text height

# D5 stroke floors (Sean confirmed 2026-10-03): thinnest glyph stroke allowed.
STROKE_FLOOR_INLAID = 0.7   # flush inlay, >= 1.75 first-layer lines
STROKE_FLOOR_RAISED = 0.9   # free-standing raised strokes
# Narrowest glyph gap (counter, letter or line) allowed on RAISED text
# (pst-l4hsl): below ~0.5 mm the slicer closes it up (labels-spike.md, gap
# analysis). Inlaid gaps are card material, held to 0.9 by the print audit.
MIN_GAP_RAISED = 0.5

# D6 text rules: at most 24 printable ASCII characters (0x20-0x7E).
MAX_TEXT_LENGTH = 24
TEXT_CHARSET = 'printable-ascii'
