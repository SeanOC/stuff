"""Deliberately regenerate ALL THREE baselines; a reason and audit provenance are required."""
import argparse
import importlib.metadata
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import compare_audit_rows, compare_bake, geometry_baseline
from scripts.baseline_common import BASELINES, ROOT, load_waivers, write_json


def nonempty(value):
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return value.strip()


def validate_inventory(rows):
    from holders.registry import resolve_colour_parts
    from profiles import PROFILES
    expected = set()
    for spec, preset in geometry_baseline.preset_specs():
        stem = f"{spec.slug}/{preset.id}"
        expected.update(f"{stem}.{suffix}" for suffix in ("stl", "glb", "png"))
        if spec.is_multi_colour:
            expected.add(f"{stem}.3mf")
            expected.update(f"{stem}.{profile}.3mf" for profile in PROFILES)
            expected.update(f"{stem}-{name}.stl"
                            for name, _, _ in resolve_colour_parts(spec, preset.values))
    if set(rows) != expected:
        raise ValueError(f"incomplete app-preset bake: missing={sorted(expected - rows.keys())}, "
                         f"extra={sorted(rows.keys() - expected)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--why", required=True, type=nonempty)
    parser.add_argument("--audit-rows", required=True, type=Path)
    parser.add_argument("--audit-source", required=True, type=nonempty,
                        help="CI run id and source SHA for the downloaded jobs")
    args = parser.parse_args(argv)
    load_waivers()  # Fail on malformed waiver policy before expensive work.
    audit, scope = compare_audit_rows.collect(args.audit_rows)
    keys = geometry_baseline.preset_keys()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    manifest_keys = sorted(f"{model['slug']}/{preset['id']}"
                           for model in manifest["models"] for preset in model["presets"])
    if sorted(keys) != manifest_keys:
        raise ValueError("registry app presets differ from manifest; regenerate manifest first")
    header = {
        "schema_version": 1, "why": args.why,
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "build123d": importlib.metadata.version("build123d"),
        "cadquery-ocp-novtk": importlib.metadata.version("cadquery-ocp-novtk"),
        "preset_scope": "all manifest app presets; smoke registrations excluded",
        "presets": keys,
    }
    start = time.monotonic()
    geometry = geometry_baseline.collect()
    print(f"geometry baseline: {len(geometry)} presets, {time.monotonic() - start:.3f}s",
          flush=True)
    with tempfile.TemporaryDirectory(prefix="bd123-baseline-") as temporary:
        directory = Path(temporary) / "bake"
        subprocess.run([sys.executable, str(ROOT / "scripts/export.py"),
                        "--presets-only", str(directory)], cwd=ROOT, check=True)
        bake, diagnostics = compare_bake.collect(directory)
        validate_inventory(bake)
    documents = {
        "geometry": {"header": {**header, "kind": "geometry"}, "rows": geometry},
        "bake": {"header": {**header, "kind": "bake"}, "rows": bake,
                 "diagnostics": diagnostics},
        "audit-rows": {
            "header": {**header, "kind": "audit-rows", "job_scope": scope,
                       "audit_source": args.audit_source,
                       "row_scope": "measurement rows joined by (nodeid, name) in the declared CI jobs, "
                                    "including endpoint/corner tests beyond the app presets; "
                                    "session/collection/outcome rows validate capture integrity"},
            "rows": audit,
        },
    }
    # Collect everything successfully before replacing any committed baseline.
    for kind, document in documents.items():
        write_json(BASELINES / kind / f"{kind}-baseline.json", document)
        print(f"wrote {kind}: {len(document['rows'])} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
