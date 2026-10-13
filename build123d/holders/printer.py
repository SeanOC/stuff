"""The target printer's build volume (design-guidelines.md, "Target printer").

Bambu Lab H2S printing with ONE nozzle — the declared 0.4 mm single-nozzle
+ AMS multi-colour workflow — has a 325 x 320 x 325 mm build volume (X x Y x
Z). Using both nozzles shrinks X to 300; 350 x 320 x 325 is the enclosure,
not a printable volume (bead pst-p3bb3).

Production code (a model's Param maxima) and the print audit
(tests/print_audit.py) both read these, so they live outside tests/, which
the bd-render image does not ship.
"""

BED_X = 325.0  # mm, single-nozzle
BED_Y = 320.0  # mm
BED_Z = 325.0  # mm, build height
