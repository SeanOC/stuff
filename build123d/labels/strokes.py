"""Regenerate the committed tombstone strokes: python -m labels.strokes --regen."""
from __future__ import annotations

import argparse
import json
from functools import lru_cache

from labels import label_text as lt


def regenerate() -> None:
    """Record each layout candidate with a fresh scan, then replace the JSON.

    Use the frame/layout only: generating solids is unnecessary. Restore all
    in-memory caches even on failure, and write only after every preset passes.
    """
    from holders import tombstone_sign as sign

    measured: dict[str, float] = {}
    original = lt._nominal_stroke

    @lru_cache(maxsize=None)
    def recording(text, path=str(lt.FONT_PATH), style=lt.FONT_STYLE):
        stroke = lt.measure_stroke(text, path, style)
        measured[lt.stroke_key(text, path, style)] = stroke
        return stroke

    lt._font_sha.cache_clear()
    lt._nominal_stroke = recording
    sign._ink.cache_clear()
    try:
        for preset in sign.SPEC.presets:
            sign._frame(sign.SPEC.resolve_values(preset.values))
            print(f'{preset.id}: {len(measured)} lines measured', flush=True)
        previous = len(lt.stroke_cache())
        lt.STROKE_CACHE.write_text(json.dumps(dict(sorted(measured.items())), indent=1) + '\n',
                                  encoding='utf-8')
        print(f'wrote {previous} -> {len(measured)} strokes to {lt.STROKE_CACHE}')
    finally:
        lt._nominal_stroke = original
        original.cache_clear()
        lt.stroke_cache.cache_clear()
        sign._ink.cache_clear()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--regen', action='store_true', required=True,
                        help='replace cached strokes with live measurements')
    parser.parse_args(argv)
    regenerate()


if __name__ == '__main__':
    main()
