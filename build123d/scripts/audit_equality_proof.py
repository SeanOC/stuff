"""One-off before/after equality proof for a print_audit speed-up (pst-bzahj).

NOT a permanent test. A pytest plugin: every ``audit(...)`` call any test makes
also runs the REFERENCE audit (tests/print_audit.py at git ref ``AUDIT_REF``,
default origin/main) on the same arguments and records both reports and CPU
times. At session end the plugin fails the run if any field differs (floats
to 1e-6, everything else exact — downward fillets compare by geometry type,
location and angle, i.e. the same offending faces).

    AUDIT_PROOF_DIR=../.tmp-pst-bzahj/proof uv run pytest -p scripts.audit_equality_proof \\
        tests/test_print_audit.py tests/test_spool_cradle.py ... -q -n 4
    uv run python scripts/audit_equality_proof.py ../.tmp-pst-bzahj/proof   # summary
"""
from __future__ import annotations

import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = os.environ.get("AUDIT_REF", "origin/main")
OUT = Path(os.environ.get("AUDIT_PROOF_DIR", ROOT.parent / ".tmp-audit-proof"))
TOL = 1e-6


def _load_reference():
    src = subprocess.run(
        ["git", "show", f"{REF}:build123d/tests/print_audit.py"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout
    path = OUT / "reference_print_audit.py"
    path.write_text(src)
    spec = importlib.util.spec_from_file_location("_reference_print_audit", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _diff(a, b, path=""):
    """Field paths where ``a`` and ``b`` differ (floats to TOL)."""
    if isinstance(a, float) and isinstance(b, (int, float)):
        return [] if abs(a - b) <= TOL else [f"{path}: {a!r} != {b!r}"]
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return [f"{path}: len {len(a)} != {len(b)}"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, f"{path}[{i}]")]
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            return [f"{path}: keys differ"]
        return [d for k in a for d in _diff(a[k], b[k], f"{path}.{k}")]
    return [] if a == b else [f"{path}: {a!r} != {b!r}"]


def _install():
    sys.path.insert(0, str(ROOT))
    OUT.mkdir(parents=True, exist_ok=True)
    ref = _load_reference()
    from tests import print_audit as new  # the module every test imports `audit` from
    fast = new.audit
    log = OUT / f"records-{os.environ.get('PYTEST_XDIST_WORKER', 'main')}-{os.getpid()}.jsonl"

    def audit(part, orientation=(0.0, 0.0, 1.0), **kwargs):
        t0 = time.process_time()
        got = fast(part, orientation, **kwargs)
        t_new = time.process_time() - t0
        t0 = time.process_time()
        want = ref.audit(part, orientation, **kwargs)
        t_ref = time.process_time() - t0
        g, w = dataclasses.asdict(got), dataclasses.asdict(want)
        rec = dict(test=os.environ.get("PYTEST_CURRENT_TEST", "?").rsplit(" (", 1)[0],
                   model=got.model, ok=got.ok, t_new=t_new, t_ref=t_ref,
                   diffs=_diff(g, w), report=g)
        with log.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        return got

    new.audit = audit


def summarise(out_dir: Path) -> int:
    recs = [json.loads(line) for f in sorted(out_dir.glob("records-*.jsonl"))
            for line in f.read_text().splitlines()]
    bad = [r for r in recs if r["diffs"]]
    print("| audit call (test) | model | ok | reference CPU s | new CPU s | identical |")
    print("|---|---|---|---:|---:|---|")
    for r in sorted(recs, key=lambda r: r["test"]):
        print(f"| {r['test']} | {r['model']} | {r['ok']} | {r['t_ref']:.2f} "
              f"| {r['t_new']:.2f} | {'yes' if not r['diffs'] else 'NO: ' + '; '.join(r['diffs'])} |")
    t_ref = sum(r["t_ref"] for r in recs)
    t_new = sum(r["t_new"] for r in recs)
    print(f"\n{len(recs)} audit calls, {len(bad)} differing; reference {t_ref:.1f} s, "
          f"new {t_new:.1f} s CPU ({100 * (1 - t_new / t_ref):.0f} % less)")
    return 1 if bad or not recs else 0


def pytest_sessionfinish(session, exitstatus):
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return
    bad = sum(1 for f in OUT.glob("records-*.jsonl")
              for line in f.read_text().splitlines() if json.loads(line)["diffs"])
    if bad:
        print(f"\naudit_equality_proof: {bad} audit call(s) DIFFER from {REF}")
        session.exitstatus = 1


if __name__ == "__main__":
    sys.exit(summarise(Path(sys.argv[1])))
else:
    _install()
