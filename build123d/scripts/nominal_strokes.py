"""Regenerate labels/nominal_strokes.json from live scans (pst-tl4ac.3).

Builds every tombstone sign preset with the cache bypassed, records each
(text, face) whose nominal stroke the layout asked for, and writes the live
measurements. Run after changing a preset string, a vendored font or the
stroke scan in labels/label_text.py:

    uv run python scripts/nominal_strokes.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from labels import label_text as lt  # noqa: E402
from holders import tombstone_sign as m  # noqa: E402


def main() -> None:
    measured: dict[str, float] = {}
    live = lt.measure_stroke

    def recording(text, path=lt.FONT_PATH, style=lt.FONT_STYLE):
        stroke = live(text, path, style)
        measured[lt.stroke_key(text, path, style)] = stroke
        return stroke

    lt.stroke_cache.cache_clear()
    lt.stroke_cache = lambda: {}
    lt.measure_stroke = recording
    for preset in m.SPEC.presets:
        m.colour_parts(m.SPEC.resolve_values(preset.values))
        print(f'{preset.id}: {len(measured)} lines measured', flush=True)
    lt.STROKE_CACHE.write_text(json.dumps(dict(sorted(measured.items())), indent=1) + '\n',
                               encoding='utf-8')
    print(f'wrote {len(measured)} strokes to {lt.STROKE_CACHE}')


if __name__ == '__main__':
    main()
