"""Audit the revised round-hole and maximum-slot ear geometries.

From build123d/: PYTHONPATH=. uv run python tools/rack10_ear_probe.py
The rev 1 U-boundary datum fixes the original 0.55 mm ligament conflict.
"""
from rack10.panel import panel
from tests.print_audit import audit


def main():
    ok = True
    for slot in (0,8):
        report = audit(panel(1,slot_mm=slot),model=f'rack10-ear-slot-{slot}')
        print(report.format())
        ok &= report.ok
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
