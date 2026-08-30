# build123d PoC — "manufacturing as code" experiment

Parametric models in **Python + [build123d](https://github.com/gumyr/build123d)**, consuming **published
parametric libraries as dependencies** — evaluated against our OpenSCAD workflow (see repo root).

## Hard rule
openGrid / Multiconnect geometry comes **only** from the pinned
[`opengrid` library](https://makerrepo.com/r/fangpenlin/opengrid/) (MIT, build123d-native) or other
existing build123d ecosystem libraries. **No home-grown mount geometry. No porting from our SCAD.**
If a library can't do something, that's a *finding for the eval*, not an invitation to work around it.

## Layout
- `holders/registry.py` — model registry; registering a model buys it export + tests automatically
- `holders/smoke.py` — library-provided smoke artifacts (tile, MC round head)
- `holders/cylindrical.py` — the PoC parametric C-ring holder (lands via its bead)
- `scripts/export.py` — STL (print) + GLB (viewer) + PNG (3-view review render) per model → `out/`
- `viewer/index.html` — drag-drop GLB viewer (model-viewer, static, no build)
- `tests/` — registry-driven: every model must build, be watertight, have volume; library dims pinned

## Commands
```bash
uv sync              # env (Python ≥3.13, uv.lock pinned, opengrid pinned by commit)
uv run pytest tests/ # registry-driven checks
uv run python scripts/export.py   # build everything → out/
```

## Eval dimensions (vs OpenSCAD)
agent workability · geometry/output quality (real fillets) · CI fit · preview experience
