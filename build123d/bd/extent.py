"""``bd extent``: the print-frame extent and bed verdict of a cached part
(pst-ptl41 C2), measured as the registry bed gate does
(tests/test_print_audit.py test_audit_full_only_presets_fit_the_bed)."""

from __future__ import annotations

from bd import build


def run(args) -> tuple[int, str, dict]:
    from holders.printer import BED_X, BED_Y, BED_Z
    from tests.print_audit import _unit, bed_failure, print_extent

    entry = build.entry_for(args.target, args.preset, args.param, rebuild=args.rebuild)
    spec = build.find_spec(entry.meta["model"])
    values = entry.meta["params"]
    part = entry.load()
    if spec.print_frame:
        part = spec.print_frame(values) * part
    extent = print_extent(part, _unit(spec.print_orientation))
    bed = (BED_X, BED_Y, BED_Z)
    failure = bed_failure(extent, bed=bed)
    a, b, h = extent
    summary = (f"{entry.key}  {spec.name}  extent {a:.1f} × {b:.1f} × {h:.1f} mm  "
               + ("fits the bed" if failure is None else f"FAIL: {failure}"))
    return (0 if failure is None else 1), summary, {
        "key": entry.key, "model": spec.name, "extent_mm": list(extent),
        "bed_mm": list(bed), "fits": failure is None, "failure": failure}
