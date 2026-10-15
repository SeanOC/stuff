"""pst-ptl41 (stage 2a): `uv run python -m bd` build / audit / extent.

Unmarked on purpose: it runs in the bd123 fast job on every PR, because a
part-cache key that misses a source edit would silently serve stale
geometry to every bd query. Uses underware_l (0.4 s build, ~1.5 s audit).
"""

import dataclasses
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bd import build, cli  # noqa: E402
from tests import audit_cache  # noqa: E402

SLUG = "underware-l"


@pytest.fixture(autouse=True)
def part_cache(tmp_path, monkeypatch):
    cache = tmp_path / "parts"
    monkeypatch.setenv("BD_PART_CACHE", str(cache))
    return cache


def bd(capsys, *argv):
    """(exit code, the one JSON object printed) for `bd <argv> --json`."""
    capsys.readouterr()
    code = cli.main([*argv, "--json"])
    out = capsys.readouterr().out
    lines = out.strip().splitlines()
    assert len(lines) == 1, f"--json must print exactly one line, got {out!r}"
    return code, json.loads(lines[0])


def test_build_then_hit_then_rebuild(capsys, part_cache):
    code, first = bd(capsys, "build", SLUG)
    assert code == 0 and first["hit"] is False
    assert (part_cache / f"{first['key']}.brep").exists()
    meta = json.loads((part_cache / f"{first['key']}.json").read_text())
    for field in ("slug", "params", "versions", "source_hash", "bbox", "volume", "build_s"):
        assert field in meta, field
    assert meta["volume"] > 0

    code, second = bd(capsys, "build", SLUG)
    assert code == 0 and second["hit"] is True and second["key"] == first["key"]

    code, third = bd(capsys, "build", SLUG, "--rebuild")
    assert code == 0 and third["hit"] is False and third["key"] == first["key"]


def test_preset_and_param_resolve_to_the_same_key(capsys):
    """The key is over RESOLVED values: a preset and the same values spelled
    as --param land on one cache entry; a different value is a different key."""
    spec = build.find_spec(SLUG)
    preset = spec.presets[0]
    _, by_preset = bd(capsys, "build", SLUG, "--preset", preset.id)
    pairs = [f"{k}={json.dumps(v) if isinstance(v, bool) else v}"
             for k, v in preset.values.items()]
    argv = [a for p in pairs for a in ("--param", p)]
    _, by_param = bd(capsys, "build", SLUG, *argv)
    assert by_param["key"] == by_preset["key"] and by_param["hit"] is True
    _, other = bd(capsys, "build", SLUG, "--param", "channel_total_height=30")
    assert other["key"] != by_preset["key"]


# --- C1: the source hash ---------------------------------------------------

@pytest.fixture
def tree(tmp_path):
    """A copy of the hashed part of build123d/ (the hasher's root)."""
    copy = tmp_path / "build123d"
    for rel in build.hashed_files(build.ROOT):
        (copy / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(build.ROOT / rel, copy / rel)
    return copy


def _key(root):
    return build.part_key("underware_l", {"channel_total_height": 22}, root=root)


def test_hash_covers_the_runtime_inputs():
    """Non-.py builder inputs and every geometry tree are hashed."""
    files = {p.as_posix() for p in build.hashed_files()}
    for rel in ("labels/label_text.py", "labels/nominal_strokes.json",
                "assets/fonts/inter/Inter-Bold.ttf", "capture/sheets.json",
                "holders/registry.py", "holders/printer.py",
                "opengrid_snap/constants.py"):
        assert rel in files, rel
    tops = {p.split("/")[0] for p in files}
    assert not tops & (build.NON_GEOMETRY | build.GENERATED_TOP), tops
    assert not any(p.endswith((".pyc", ".pyo")) or "__pycache__" in p for p in files)


def test_python_source_edit_moves_the_key(tree):
    before = _key(tree)
    with open(tree / "labels/label_text.py", "a") as f:
        f.write("\n# pst-ptl41 key test\n")
    assert _key(tree) != before


def test_data_file_edit_moves_the_key_with_every_py_unchanged(tree):
    before = _key(tree)
    with open(tree / "labels/nominal_strokes.json", "ab") as f:
        f.write(b" ")
    assert _key(tree) != before


def test_generated_and_non_geometry_files_do_not_move_the_key(tree):
    before = _key(tree)
    for rel in (".cache/parts/x.brep", ".cache/audit/x.json", "baked/x/x.stl",
                "out/x.glb", "holders/__pycache__/x.cpython-314.pyc",
                "labels/stray.pyc", ".venv/lib/x.py", "tests/test_x.py",
                "docs/x.md", "bd/x.py", "scripts/x.py"):
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_bytes(b"generated")
    assert _key(tree) == before


# --- C2: queries read the cached part --------------------------------------

def test_queries_on_a_key(capsys, monkeypatch):
    _, built = bd(capsys, "build", SLUG)
    key = built["key"]
    # A query on a key must never build.
    spec = build.find_spec(SLUG)
    calls = []
    monkeypatch.setattr(build, "find_spec", lambda s: dataclasses.replace(
        spec, build=lambda v: calls.append(v)) if s in (spec.name, spec.slug) else None)

    code, report = bd(capsys, "audit", key)
    assert code == 0 and report["ok"] is True and report["failures"] == []
    assert report["report"]["model"] == "underware_l"
    assert report["report"]["min_wall_mm"] >= 0.9

    code, ext = bd(capsys, "extent", key)
    assert code == 0 and ext["fits"] is True and ext["failure"] is None
    assert ext["extent_mm"] == report["report"]["extent_mm"]
    assert calls == []


def test_query_by_slug_builds_once_then_hits(capsys):
    code, ext = bd(capsys, "extent", SLUG)
    assert code == 0
    _, again = bd(capsys, "build", SLUG)
    assert again["hit"] is True and again["key"] == ext["key"]


def test_cached_part_audits_like_a_fresh_build():
    """The reloaded BREP has the fresh build's audit-cache key, so `bd audit`
    and the registry audit test share one cache entry and one verdict."""
    from tests.test_print_audit import _audit_args

    entry = build.build(SLUG)
    spec = build.find_spec(SLUG)
    fresh, kwargs = _audit_args(spec)
    assert audit_cache.key(entry.load(), **kwargs) == audit_cache.key(fresh, **kwargs)


def test_human_summary_is_one_line(capsys):
    assert cli.main(["build", SLUG]) == 0
    out = capsys.readouterr().out
    assert len(out.strip().splitlines()) == 1 and "underware_l" in out
    assert cli.main(["extent", SLUG]) == 0
    assert len(capsys.readouterr().out.strip().splitlines()) == 1


# --- C3 / C4: usage and param errors exit 2 --------------------------------

@pytest.mark.parametrize("argv, text", [
    (["build", SLUG, "--param", "channel_total_height=abc"], "expected a number"),
    (["build", SLUG, "--param", "channel_total_height=1"], "< min"),
    (["build", SLUG, "--param", "nope=1"], "unknown param 'nope'"),
    (["build", SLUG, "--param", "channel_total_height"], "expects k=v"),
    (["build", SLUG, "--preset", "nope"], "unknown preset"),
    (["build", "no-such-model"], "unknown model"),
    (["audit", "0" * 64], "no cached part"),
])
def test_usage_errors_exit_2(capsys, argv, text):
    code, out = bd(capsys, *argv)
    assert code == 2 and text in out["error"]


def test_model_value_error_exits_2(capsys, monkeypatch):
    """C3: the model's own build(values) ValueError is a usage error."""
    spec = build.find_spec(SLUG)

    def reject(values):
        raise ValueError("width too small for the cutouts")
    monkeypatch.setattr(build, "find_spec",
                        lambda s: dataclasses.replace(spec, build=reject))
    code, out = bd(capsys, "build", SLUG)
    assert code == 2 and "width too small for the cutouts" in out["error"]


def test_module_entry_point(part_cache):
    """`python -m bd` from build123d/ (the only supported invocation)."""
    proc = subprocess.run([sys.executable, "-m", "bd", "build", "--help"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0 and "slug" in proc.stdout
    proc = subprocess.run([sys.executable, "-m", "bd", "frobnicate"],
                          cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 2 and "Traceback" not in proc.stderr
