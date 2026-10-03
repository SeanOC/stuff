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

# D6 text rules: at most 24 printable ASCII characters (0x20-0x7E).
MAX_TEXT_LENGTH = 24
TEXT_CHARSET = 'printable-ascii'

# D8 label holder on holder_spool_cradle's front panel (L3, pst-o9sd4): two
# side rails and a bottom lip; the card slides in from the top, spool removed.
# Each rail is an L in plan: an outer wall (RAIL_W - LIP_OVERLAP) beside the
# card edge + clearance, and a LIP_T shelf in front of the card that covers
# LIP_OVERLAP of its face. The lip is the same section along the bottom.
SLOT_CLEARANCE = 0.2                    # card to slot, per side, every axis
SLOT_DEPTH = CARD_T+2*SLOT_CLEARANCE    # 2.0
LIP_T = 1.2                             # retaining shelf, in front of the card
LIP_OVERLAP = 1.5                       # shelf over the card face; < TEXT_MARGIN
RAIL_PROUD = SLOT_DEPTH+LIP_T           # 3.2: rail/lip stand-off from the panel face
RAIL_W = 2.5                            # LIP_OVERLAP + a 1.0 outer wall (>= 0.9 MIN_WALL)
SIDE_INSET = 0.5                        # MINIMUM rail outer face to panel side (0.4 rim chamfer)
HOLDER_MIN_PANEL_W = CARD_W+2*SLOT_CLEARANCE+2*(RAIL_W-LIP_OVERLAP)+2*SIDE_INSET  # 63.4
HOLDER_TOP_INSET = 2.0                  # rail tops below the panel top: clears junction + 0.4 rim
HOLDER_JUNCTION = 1.0                   # 45-degree blend where rails/lip meet the panel face
