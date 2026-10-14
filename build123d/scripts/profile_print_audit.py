"""Profile tests/print_audit.audit() per phase (bead pst-bzahj, CI P8 spike).

Builds each case once, then times every audit phase separately (CPU seconds,
``time.process_time``) and counts the OCCT point-classifier calls each phase
makes. The phase table lands in docs/print-audit-profile.md.

    uv run python scripts/profile_print_audit.py              # all cases
    uv run python scripts/profile_print_audit.py cup_lid      # one case
    uv run python scripts/profile_print_audit.py --cprofile cradle_default

Dev-only: imports nothing the audit itself does not already import, plus the
stdlib profiler.
"""
from __future__ import annotations

import cProfile
import pstats
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from build123d import Face, Solid  # noqa: E402

from holders.registry import all_models  # noqa: E402
from tests import audit_cache  # noqa: E402
from tests import print_audit as pa  # noqa: E402
from tests.test_print_audit import _audit_args  # noqa: E402
from tests.test_spool_cradle import PRINT_CORNER  # noqa: E402

SPECS = {s.name: s for s in all_models()}


def _drawer_container(values):
    """(print_frame, exclusions) exactly as test_endpoint_audit_and_edges."""
    from holders import openconnect_drawer as m
    from tests.openconnect_drawer_inventory import container_wall_regions
    return m.print_frame(values), m.audit_exclusions(values) + container_wall_regions(values)


# name -> (spec, values[, audit_args]). audit_args(values) returns the
# (print_frame, exclusions) of a caller that audits outside _build_and_audit;
# such a case has no mount cutters and audits +Z after the frame.
CASES = {
    "cradle_default": ("holder_spool_cradle", {}),
    "cradle_diagonal_root_corner": ("holder_spool_cradle", PRINT_CORNER),
    "cup_lid": ("holder_cup_lid", {}),
    # pst-vhywk: the slowest audit_full item before D4 (738 s in .test_durations).
    "drawer_container_vertical_grids_8": (
        "openconnect_drawer", {"part": "container", "vertical_grids": 8}, _drawer_container),
}


def build_case(name):
    """(part, up, boxes, hmin, audit kwargs) exactly as the case's test audits it.

    The part comes from the registry audit's own _audit_args. The set-up
    below mirrors print_audit._audit (frame, then exact-exclusion wrapping),
    so the phases see what audit() hands them. The returned part is already
    framed, so the end-to-end audit() gets no print_frame.
    """
    spec_name, raw, *audit_args = CASES[name]
    part, kwargs = _audit_args(SPECS[spec_name], raw)
    if audit_args:
        frame, exclusions = audit_args[0](raw)
        kwargs.update(orientation=(0.0, 0.0, 1.0), cutters=[],
                      exclusions=exclusions, print_frame=frame)
    frame = kwargs.pop("print_frame")
    cutters, exclusions = list(kwargs["cutters"]), list(kwargs["exclusions"])
    if frame is not None:
        part = frame * part
        cutters = [frame * c for c in cutters]
        exclusions = [frame * e for e in exclusions]
    kwargs.update(cutters=cutters, exclusions=exclusions)
    up = pa._unit(kwargs["orientation"])
    boxes = pa._cutter_boxes(cutters) + [
        pa._ExactExclusion(e) if hasattr(e, "wrapped") else e for e in exclusions]
    hmin = min(pa._height(v, up) for v in part.vertices())
    return part, up, boxes, hmin, kwargs


COUNTS: Counter = Counter()


def _counting(cls, attr, key):
    orig = getattr(cls, attr)

    def wrapped(self, *a, **k):
        COUNTS[key] += 1
        return orig(self, *a, **k)

    setattr(cls, attr, wrapped)


# Count BEFORE timing would distort the times, so counts come from a separate
# pass with the wrappers installed (see main()).
def install_counters():
    _counting(Solid, "is_inside", "solid.is_inside")
    if hasattr(pa, "_ClassifiedPart"):
        _counting(pa._ClassifiedPart, "is_inside", "solid.is_inside")
    _counting(Face, "is_inside", "face.is_inside")
    _counting(Face, "position_at", "face.position_at")
    _counting(Face, "normal_at", "face.normal_at")


def phases(part, up, boxes, hmin):
    # audit() hands the phases a classifier-reusing proxy when it has one.
    part = pa._ClassifiedPart(part) if hasattr(pa, "_ClassifiedPart") else part
    return [
        ("overhang", lambda: pa._max_overhang(part, up, boxes, hmin)),
        ("bridge", lambda: pa._longest_bridge(part, up, boxes, hmin)),
        ("min wall", lambda: pa._min_wall(part, up, boxes)),
        ("curved faces", lambda: pa._downward_curved_faces(part, up, boxes, hmin)),
        ("bed chamfer", lambda: pa._bed_chamfer(part, up, hmin)),
    ]


def run(name, counted):
    part, up, boxes, hmin, kwargs = build_case(name)
    nfaces = len(part.faces())
    rows = []
    for label, fn in phases(part, up, boxes, hmin):
        COUNTS.clear()
        t0 = time.process_time()
        fn()
        dt = time.process_time() - t0
        rows.append((label, dt, dict(COUNTS) if counted else {}))
    t0 = time.process_time()
    with audit_cache.disabled():  # a cache hit would time the lookup, not the audit
        pa.audit(part, **kwargs)
    total = time.process_time() - t0
    return nfaces, len(boxes), rows, total


def main(argv):
    do_cprofile = "--cprofile" in argv
    names = [a for a in argv if not a.startswith("--")] or list(CASES)
    names = [n for n in CASES for a in names if a in n]
    if do_cprofile:
        for name in names:
            part, *_rest, kwargs = build_case(name)
            prof = cProfile.Profile()
            prof.enable()
            with audit_cache.disabled():
                pa.audit(part, **kwargs)
            prof.disable()
            print(f"== cProfile {name}")
            pstats.Stats(prof).sort_stats("tottime").print_stats(15)
        return
    timed = {n: run(n, counted=False) for n in names}
    install_counters()
    counted = {n: run(n, counted=True) for n in names}
    for name in names:
        nfaces, nboxes, rows, total = timed[name]
        crow = {label: c for label, _dt, c in counted[name][2]}
        print(f"\n### {name}  ({nfaces} faces, {nboxes} cutter/exclusion regions)")
        print("| phase | CPU s | % | Solid.is_inside | Face.is_inside | position_at | normal_at |")
        print("|---|---:|---:|---:|---:|---:|---:|")
        phase_sum = sum(dt for _l, dt, _c in rows)
        for label, dt, _ in rows:
            c = crow[label]
            print(f"| {label} | {dt:.2f} | {100 * dt / phase_sum:.0f} "
                  f"| {c.get('solid.is_inside', 0)} | {c.get('face.is_inside', 0)} "
                  f"| {c.get('face.position_at', 0)} | {c.get('face.normal_at', 0)} |")
        print(f"| **sum of phases** | **{phase_sum:.2f}** | | | | | |")
        print(f"| audit() end-to-end | {total:.2f} | | | | | |")


if __name__ == "__main__":
    main(sys.argv[1:])
