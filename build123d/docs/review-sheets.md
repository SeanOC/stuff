# Model review sheets

Regenerate default-model review artifacts from the repo root:

```sh
uv run --project build123d python build123d/scripts/export.py --commit-review
uv run --project build123d pytest build123d/tests/test_review_sheet.py
```

The exporter writes `out/<name>.png` for the advisory reviewer (whose mount
rubric lookup uses the basename). `--commit-review` also writes each registered
non-smoke model's sheet to `docs/renders/review/<slug>.png` and its analytic
section outline to `docs/renders/sections/<slug>.svg`. Review these diffs when
changing geometry. The SVGs are pytest-regressions goldens, rounded to three
decimal places with disconnected outlines sorted for reproducibility.
The specialised spool-cradle validation sheet has its own renderer.

The five tiles are ISO, FRONT, TOP, SECTION, and UNDERSIDE. Orange faces mark
the section cut; blue-grey faces are retained material behind the cut. The
section tile retains the negative half of the declared normal and looks from
the positive side. The SVG records only the intersection at the plane, so it
need not contain every surface visible behind the cut in the PNG.

`ModelSpec.review_sections` holds static planes in model-space millimetres.
Only the first plane is rendered. If no plane is declared, mounted models use
the first seat, with normal `face_normal × entry_axis`; unmounted models use
the bounding-box centre and +X. The cradle's declared plane is X=0, with an
origin at its default saddle centre Y=110 mm. This reveals the far truss and
the cut back/front panels.

The GLB frame differs from the model: `(x, y, z)` mm maps to `(x, z, -y)` m.
Both section planes and the underside camera use the named conversion helpers
in `scripts/thumbnail.py`. The underside eye is opposite the transformed
`print_orientation`, exposing the bed-facing surfaces. Callers without a
`ReviewContext` retain the legacy three-view output.

Capped sections use Trimesh with Shapely and mapbox-earcut. NetworkX and Rtree
are also required for nested section loops (including the cup lid).

## Initial validation (pst-kge4)

At 400 px per tile, measured render times (GLB load, all five views, PNG write;
excluding CAD build/export and analytic SVG) were:

| Model | Seconds | Default volume, before = after (mm³) |
| --- | ---: | ---: |
| holder-cup-lid | 1.185 | 16085.414802 |
| holder-spray-can | 0.678 | 46093.514430 |
| holder-bottle-500ml | 0.614 | 47929.490193 |
| holder-spool-cradle | 0.976 | 72672.427977 |
| smoke-opengrid-tile-1x1 | 0.239 | 983.292005 |
| smoke-multiconnect-roundhead | 0.401 | 1007.927643 |

Every default and preset volume matched the baseline exactly (15 builds):

| Preset | Before = after (mm³) |
| --- | ---: |
| cup lid / sippy_cup_85mm | 16085.414802 |
| spray can / spray_can | 46093.514430 |
| spray can / spray_can_light | 43166.833167 |
| spray can / spray_can_robust | 55600.908494 |
| bottle / bottle_500ml | 47929.490193 |
| bottle / bottle_500ml_light | 45039.409634 |
| bottle / bottle_500ml_robust | 57835.443047 |
| spool cradle / bambu_reusable_200 | 72798.918568 |
| spool cradle / ams_generic_200 | 72672.427977 |

No geometry or load path changed. The cradle retains its declared worst case
of 30 N downward at the front rim, with its existing PETG/PCTG-only material
restriction. Review checklist §6.1 uses the UNDERSIDE tile to inspect bed-facing
surfaces and potential bridges; only the existing mount-pocket support exception
applies.
