"""``bd audit``: the registry print audit on a cached part (pst-ptl41 C2).

Calls tests/print_audit.py audit() unchanged, with the exact arguments the
registry audit (tests/test_print_audit.py) passes, so it goes through the
audit cache and reports what the gate reports.
"""

from __future__ import annotations

import dataclasses

from bd import build


def run(args) -> tuple[int, str, dict]:
    from tests.print_audit import audit
    from tests.test_print_audit import _audit_kwargs

    entry = build.entry_for(args.target, args.preset, args.param, rebuild=args.rebuild)
    spec = build.find_spec(entry.meta["model"])
    values = entry.meta["params"]
    report = audit(entry.load(), **_audit_kwargs(spec, values))
    verdict = "PASS" if report.ok else "FAIL: " + "; ".join(report.failures())
    summary = f"{entry.key}  {spec.name}  audit {verdict}\n{report.format()}"
    return (0 if report.ok else 1), summary, {
        "key": entry.key, "model": spec.name, "ok": report.ok,
        "failures": report.failures(), "report": dataclasses.asdict(report)}
