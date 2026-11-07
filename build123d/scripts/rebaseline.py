"""Deliberately regenerate baselines with a required reason.

For intended geometry changes, first use --geometry-only to write a provisional
geometry baseline before CI. Then regenerate all three baselines using
--audit-rows and --audit-source from the first successful CI capture. This avoids
the stale geometry assertion failing the capture needed for a full rebaseline.
Use --audit-test-file to refresh only one test file's existing audit rows from
a complete successful capture, preserving all unrelated baseline measurements.
Use --new-model with a model-scoped audit capture to add a new registry model
to all three baselines without regenerating existing measurements.
"""
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
from scripts.baseline_common import BASELINES, ROOT, load_waivers, read_baseline, write_json


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


def refresh_audit_file(args, rows, scope):
    path = BASELINES / "audit-rows" / "audit-rows-baseline.json"
    document = read_baseline("audit-rows", path)
    prefix = args.audit_test_file + "::"
    expected = {key for key in document["rows"] if json.loads(key)[0].startswith(prefix)}
    if not expected or set(rows) != expected:
        raise ValueError(f"audit test-file inventory mismatch: missing={sorted(expected - rows.keys())}, "
                         f"extra={sorted(rows.keys() - expected)}")
    for key, row in rows.items():
        old = document["rows"][key]
        document["rows"][key] = {field: row[field] for field in old if field in row} | row
    document["header"].setdefault("scoped_updates", []).append({
        "test_file": args.audit_test_file, "why": args.why,
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "build123d": importlib.metadata.version("build123d"),
        "cadquery-ocp-novtk": importlib.metadata.version("cadquery-ocp-novtk"),
        "audit_source": args.audit_source, "job_scope": scope,
    })
    write_json(path, document, sort_keys=False)
    print(f"wrote audit-rows: {len(rows)} rows for {args.audit_test_file}")
    return 0


def add_new_model(args, audit, scope):
    from holders.registry import all_models, resolve_colour_parts
    from scripts.export import bake_preset, preset_files

    spec = next((spec for spec in all_models() if spec.name == args.new_model), None)
    if spec is None or spec.is_smoke:
        raise ValueError(f"--new-model requires an app-listed registry name: {args.new_model}")
    if not audit:
        raise ValueError("--new-model requires a nonempty model-scoped audit capture")
    paths = {kind: BASELINES / kind / f"{kind}-baseline.json"
             for kind in ("geometry", "bake", "audit-rows")}
    documents = {kind: read_baseline(kind, path) for kind, path in paths.items()}
    prefix = spec.slug + "/"
    for kind, document in documents.items():
        existing = (set(audit) & document["rows"].keys() if kind == "audit-rows" else
                    {key for key in document["rows"] if key.startswith(prefix)})
        if existing:
            raise ValueError(f"{spec.name} already has {kind} rows: {sorted(existing)}; "
                             "use --geometry-only followed by a full rebaseline, or "
                             "--audit-test-file for existing audit rows")

    presets = sorted(spec.presets, key=lambda preset: preset.id)
    geometry = {f"{spec.slug}/{preset.id}": geometry_baseline.measure(spec, preset)
                for preset in presets}
    with tempfile.TemporaryDirectory(prefix="bd123-baseline-") as temporary:
        directory = Path(temporary)
        expected, unfit = set(), []
        for preset in presets:
            expected.update(prefix + name for name in preset_files(spec, preset))
            if spec.is_multi_colour:
                expected.update(f"{prefix}{preset.id}-{name}.stl"
                                for name, _, _ in resolve_colour_parts(spec, preset.values))
            if bake_preset(spec, preset, directory / spec.slug, unfit) is None:
                raise ValueError(f"empty preset bake: {spec.slug}/{preset.id}")
        if unfit:
            raise ValueError(f"unfit preset bake: {unfit}")
        bake, diagnostics = compare_bake.collect(directory)
        if set(bake) != expected:
            raise ValueError(f"incomplete model-preset bake: missing={sorted(expected - bake.keys())}, "
                             f"extra={sorted(bake.keys() - expected)}")

    update = {
        "model": spec.name, "why": args.why,
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "build123d": importlib.metadata.version("build123d"),
        "cadquery-ocp-novtk": importlib.metadata.version("cadquery-ocp-novtk"),
        "audit_source": args.audit_source, "job_scope": scope,
        "presets": list(geometry),
    }
    additions = {"geometry": geometry, "bake": bake, "audit-rows": audit}
    # Finish all measurements and inventory checks before writing any baseline.
    for kind, document in documents.items():
        document["rows"].update(additions[kind])
        document["header"].setdefault("scoped_updates", []).append(update)
        if kind == "bake":
            document.setdefault("diagnostics", {}).update(diagnostics)
        write_json(paths[kind], document)
        print(f"added {kind}: {len(additions[kind])} rows for {spec.name}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--why", required=True, type=nonempty)
    parser.add_argument("--geometry-only", action="store_true",
                        help="write only a provisional geometry baseline before CI")
    parser.add_argument("--audit-rows", type=Path)
    parser.add_argument("--audit-source", type=nonempty,
                        help="capture provenance (CI run or local command, with source SHA)")
    parser.add_argument("--audit-test-file", type=nonempty,
                        help="refresh only this test file's existing audit rows from a complete capture")
    parser.add_argument("--new-model", type=nonempty,
                        help="add one new registry name using a model-scoped audit capture")
    args = parser.parse_args(argv)
    if args.new_model and (args.geometry_only or args.audit_test_file):
        parser.error("--new-model cannot be combined with --geometry-only or --audit-test-file")
    if args.geometry_only:
        if args.audit_rows is not None or args.audit_source is not None or args.audit_test_file:
            parser.error("--geometry-only cannot be combined with audit options")
    elif args.audit_rows is None or args.audit_source is None:
        parser.error("--audit-rows and --audit-source are required unless --geometry-only is used")
    load_waivers()  # Fail on malformed waiver policy before expensive work.
    if not args.geometry_only:
        audit, scope = compare_audit_rows.collect(args.audit_rows)
        if args.new_model:
            return add_new_model(args, audit, scope)
        if args.audit_test_file:
            return refresh_audit_file(args, audit, scope)
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
    if args.geometry_only:
        write_json(BASELINES / "geometry" / "geometry-baseline.json", {
            "header": {**header, "kind": "geometry",
                       "provisional": "geometry only; bake + audit-rows regenerated from the first successful CI capture"},
            "rows": geometry,
        })
        print(f"wrote provisional geometry: {len(geometry)} rows")
        return 0
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
