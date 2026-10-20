"""Measure app-preset BREPs without tessellating or exporting a bake."""
import argparse
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.baseline_common import load_waivers, read_baseline, report


def preset_specs():
    from holders.registry import all_models
    return [(spec, preset) for spec in sorted(all_models(), key=lambda s: s.slug)
            if not spec.is_smoke for preset in sorted(spec.presets, key=lambda p: p.id)]


def preset_keys():
    return [f"{spec.slug}/{preset.id}" for spec, preset in preset_specs()]


def measure(spec, preset):
    from holders.registry import in_print_frame
    values = spec.resolve_values(preset.values)
    raw = spec.build(values)
    part = in_print_frame(spec, values, raw)
    box, raw_box = part.bounding_box(), raw.bounding_box()
    low, high = list(box.min), list(box.max)
    points = [tuple(low[i] + (high[i] - low[i]) * t[i] for i in range(3))
              for t in itertools.product((.1, .3, .5, .7, .9), repeat=3)]
    return {
        "volume": part.volume,
        "faces": len(part.faces()),
        "solids": len(part.solids()),
        "raw_bounds": [list(raw_box.min), list(raw_box.max)],
        "print_bounds": [low, high],
        "print_center": list(part.center()),
        "containment": [bool(part.is_inside(point)) for point in points],
    }


def collect():
    rows = {}
    for spec, preset in preset_specs():
        key = f"{spec.slug}/{preset.id}"
        rows[key] = measure(spec, preset)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    start = time.monotonic()
    status = report("geometry", read_baseline("geometry")["rows"], collect(), load_waivers())
    print(f"geometry wall time: {time.monotonic() - start:.3f}s")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
