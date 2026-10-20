"""Offline comparator for completed CI rows*.jsonl downloads.

Scope is identified from session markers/group, never directory names.
Measurement rows are joined globally by (nodeid, name), as in the upgrade
spike. Session/collection/outcome rows validate capture completeness and test
success; they are not numerical baseline rows. Thus adding an infrastructure
test (including this bead's BREP gate) does not change the measurement inventory.
Missing jobs are NOT COMPARABLE (exit 2); missing measurement rows in a present
job scope FAIL (exit 1). Timestamps/durations are not geometry.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.baseline_common import load_waivers, read_baseline, report


class NotComparable(ValueError):
    pass


def job_id(session):
    # Preserve the selection expression: different selections are different jobs.
    return json.dumps([session["markexpr"], session["group"]], separators=(",", ":"))


def collect(directory, required_scope=None):
    jobs = {}
    for path in sorted(directory.rglob("rows*.jsonl")):
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        sessions = [r for r in records if r["kind"] == "session"]
        if len(sessions) != 1:
            raise ValueError(f"{path}: expected exactly one session; use a fresh download directory")
        scope = job_id(sessions[0])
        jobs.setdefault(scope, []).extend(records)
    if not jobs:
        raise NotComparable(f"no job sessions in {directory}")
    if required_scope is not None:
        missing = set(required_scope) - jobs.keys()
        if missing:
            raise NotComparable(f"missing job/shard scope: {sorted(missing)}")
        jobs = {job: jobs[job] for job in required_scope}
    rows = {}
    for job, records in sorted(jobs.items()):
        counts = {r["audited"] for r in records if r["kind"] == "collection"}
        # The xdist controller may report zero; workers agree on selected count.
        counts.discard(0)
        if len(counts) != 1:
            raise ValueError(f"{job}: absent or inconsistent collection counts: {counts}")
        outcomes = [r for r in records if r["kind"] == "outcome"]
        actual_count = len([r for r in outcomes if r["when"] != "teardown"])
        if actual_count != next(iter(counts)):
            raise ValueError(f"{job}: incomplete outcome rows: {actual_count}, expected {counts}")
        outcome_ids = [r["nodeid"] for r in outcomes if r["when"] != "teardown"]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError(f"{job}: duplicate outcome rows")
        if any(r["outcome"] == "failed" for r in outcomes):
            raise ValueError(f"{job}: failed test outcomes; not a successful audit capture")
        for row in records:
            if row["kind"] == "measurement":
                key = json.dumps([row["nodeid"], row["name"]], separators=(",", ":"))
                value = row["fields"]
            else:
                continue
            if key in rows:
                raise ValueError(f"duplicate audit row: {key}")
            rows[key] = value
    return rows, sorted(jobs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        baseline = read_baseline("audit-rows")
        rows, _ = collect(args.directory, baseline["header"]["job_scope"])
        return report("audit-rows", baseline["rows"], rows, load_waivers())
    except NotComparable as error:
        print(f"audit-rows: NOT COMPARABLE: {error}")
        return 2
    except (ValueError, OSError) as error:
        print(f"audit-rows: ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
