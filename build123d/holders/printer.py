"""The target printers' build volume (design-guidelines.md, "Target printers").

The targets are the Bambu Lab H2S or H2C, both printed with ONE nozzle — the
declared 0.4 mm single-nozzle + AMS multi-colour workflow.
BED_X/BED_Y/BED_Z are the H2S single-nozzle volume, 325 x 320 x 325 mm (X x Y
x Z). Using both nozzles shrinks X to 300; 350 x 320 x 325 is the enclosure,
not a printable volume (bead pst-p3bb3).

The H2C is smaller on one axis per nozzle: left 325 x 320 x 320, right
305 x 320 x 325, dual 300 x 320 x 325 (extruder_printable_area /
extruder_printable_height in profiles/bambu-h2c-0.4/project_settings.json).
A part that needs the last 5 mm of Z or the last 20 mm of X prints on the
H2S, or on the H2C only with the nozzle that reaches it. The H2C printer
profile's plate fit is checked separately at bake time (max_footprint in
scripts/export.py, #222).

Production code (a model's Param maxima) and the print audit
(tests/print_audit.py) both read these, so they live outside tests/, which
the bd-render image does not ship.
"""

BED_X = 325.0  # mm, single-nozzle
BED_Y = 320.0  # mm
BED_Z = 325.0  # mm, build height
