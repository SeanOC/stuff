"""Content-addressed preset bake cache (bead pst-aqza2).

Keys on a fixture tree (what changes a key and what must not), the import
closure, the read audit, tarball validation, and the export.py plan →
restore → bake round trip on the label card (multi-colour: part STLs ride
in the tarball by their build-time names).
"""
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import bake_cache  # noqa: E402

TREE = {
    "scripts/export.py": "from holders.registry import all_models\nfrom scripts import helper\n",
    "scripts/helper.py": "X = 1\n",
    "holders/__init__.py": "",
    "holders/registry.py": ("def all_models():\n"
                            "    from holders import a  # noqa\n"
                            "    from holders import b  # noqa\n"),
    "holders/a.py": ("from holders.registry import all_models\nfrom . import shared\n"
                     "def build():\n    import geom.deep  # function-local import\n"),
    "holders/b.py": "from holders.registry import all_models\n",
    "holders/shared.py": "Y = 2\n",
    "geom/deep.py": "Z = 3\n",  # namespace package: no __init__.py
    "assets/fonts/x.ttf": "font",
    "labels/strokes.json": "{}",
    "uv.lock": "lock",
    "pyproject.toml": "[project]",
    "tests/test_a.py": "def test(): pass\n",
    "docs/a.md": "# doc",
    "manifest.json": "{}",
    "baked/a/p.stl": "solid",
}


@pytest.fixture
def tree(tmp_path):
    for rel, text in TREE.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def key_of(root, preset="p", values=None):
    keys = bake_cache.KeyBuilder(root, root / "scripts/export.py", root / "holders/registry.py",
                                 {root / "holders/a.py", root / "holders/b.py"})
    return keys.key(root / "holders/a.py", preset, values or {"w": 1})


def test_closure_skips_registry_discovery_but_keeps_real_imports(tree):
    keys = bake_cache.KeyBuilder(tree, tree / "scripts/export.py", tree / "holders/registry.py",
                                 {tree / "holders/a.py", tree / "holders/b.py"})
    rel = {p.relative_to(tree).as_posix() for p in keys.closure(tree / "holders/a.py")}
    assert rel == {"scripts/export.py", "scripts/helper.py", "holders/__init__.py",
                   "holders/registry.py", "holders/a.py", "holders/shared.py", "geom/deep.py"}
    assert {p.relative_to(tree).as_posix() for p in keys.data} == {
        "assets/fonts/x.ttf", "labels/strokes.json"}


@pytest.mark.parametrize("rel", [
    "holders/a.py", "holders/shared.py", "geom/deep.py", "scripts/export.py",
    "scripts/helper.py", "holders/registry.py", "assets/fonts/x.ttf",
    "labels/strokes.json", "uv.lock", "pyproject.toml",
])
def test_editing_an_input_changes_the_key(tree, rel):
    before = key_of(tree)
    (tree / rel).write_text((tree / rel).read_text() + "\n# edit\n")
    assert key_of(tree) != before


@pytest.mark.parametrize("rel", [
    "holders/b.py", "tests/test_a.py", "docs/a.md", "manifest.json", "baked/a/p.stl",
])
def test_editing_a_non_input_keeps_the_key(tree, rel):
    before = key_of(tree)
    (tree / rel).write_text((tree / rel).read_text() + "\n# edit\n")
    assert key_of(tree) == before


def test_preset_id_and_values_are_in_the_key(tree):
    assert key_of(tree) == key_of(tree)
    assert key_of(tree, values={"w": 2}) != key_of(tree)
    assert key_of(tree, preset="q") != key_of(tree)


def test_a_new_data_file_changes_the_key(tree):
    before = key_of(tree)
    (tree / "assets/art").mkdir()
    (tree / "assets/art/new.svg").write_text("<svg/>")
    assert key_of(tree) != before


@pytest.fixture
def audit(tree):
    audit = bake_cache.ReadAudit(tree)
    yield audit
    audit.active = False  # audit hooks cannot be removed


def test_audit_records_reads_under_root_only(tree, audit):
    audit.take()
    (tree / "docs/a.md").read_text()
    (tree / "baked/a/p.stl").read_text()  # the bake's own output: ignored
    open(tree / "holders/shared.py").close()
    reads = {p.relative_to(tree).as_posix() for p in audit.take()}
    assert reads == {"docs/a.md", "holders/shared.py"}


def test_an_uncovered_read_is_reported(tree, audit):
    keys = bake_cache.KeyBuilder(tree, tree / "scripts/export.py", tree / "holders/registry.py",
                                 {tree / "holders/a.py", tree / "holders/b.py"})
    audit.take()
    (tree / "assets/fonts/x.ttf").read_bytes()
    (tree / "holders/shared.py").read_text()
    assert bake_cache.uncovered(audit.take(), keys.inputs(tree / "holders/a.py")) == []
    (tree / "docs/a.md").read_text()
    (tree / "holders/b.py").read_text()  # another model's module
    gaps = bake_cache.uncovered(audit.take(), keys.inputs(tree / "holders/a.py"))
    assert [p.relative_to(tree).as_posix() for p in gaps] == ["docs/a.md", "holders/b.py"]


# ── Tarballs ────────────────────────────────────────────────────────────

REQUIRED = ["p.stl", "p.glb", "p.png"]


def files(tmp_path, names):
    out = []
    for name in names:
        (tmp_path / name).write_bytes(name.encode() * 3)
        out.append(tmp_path / name)
    return out


def test_pack_is_deterministic_and_round_trips(tmp_path):
    src = files(tmp_path, REQUIRED)
    blob = bake_cache.pack(src)
    assert bake_cache.pack(list(reversed(src))) == blob
    dest = tmp_path / "out"
    assert bake_cache.unpack(blob, dest, "p", REQUIRED, False) == sorted(REQUIRED)
    for path in src:
        assert (dest / path.name).read_bytes() == path.read_bytes()


def test_multi_colour_part_stls_ride_along(tmp_path):
    names = REQUIRED + ["p.3mf", "p-base.stl", "p-inlay.stl"]
    blob = bake_cache.pack(files(tmp_path, names))
    required = REQUIRED + ["p.3mf"]
    assert bake_cache.unpack(blob, tmp_path / "out", "p", required, True) == sorted(names)
    with pytest.raises(ValueError, match="unexpected member 'p-base.stl'"):
        bake_cache.unpack(blob, tmp_path / "plain", "p", required, False)


@pytest.mark.parametrize("names, match", [
    (["p.stl", "p.glb"], "missing p.png"),
    (REQUIRED + ["q.stl"], "unexpected member 'q.stl'"),
])
def test_a_wrong_file_set_is_a_miss(tmp_path, names, match):
    blob = bake_cache.pack(files(tmp_path, names))
    with pytest.raises(ValueError, match=match):
        bake_cache.unpack(blob, tmp_path / "out", "p", REQUIRED, True)
    assert not (tmp_path / "out").exists()  # validated before anything is written


def test_path_traversal_and_garbage_are_misses(tmp_path):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as tar:
        for name in REQUIRED + ["p-../../evil.stl"]:
            info = tarfile.TarInfo(name)
            info.size = 1
            tar.addfile(info, io.BytesIO(b"x"))
    with pytest.raises(ValueError, match="unexpected member"):
        bake_cache.unpack(raw.getvalue(), tmp_path / "out", "p", REQUIRED, True)
    with pytest.raises(ValueError, match="unreadable"):
        bake_cache.unpack(b"not a tarball", tmp_path / "out", "p", REQUIRED, True)


# ── export.py round trip ────────────────────────────────────────────────

@pytest.fixture
def label_card_only(monkeypatch):
    import scripts.export as export
    from holders.label_card import SPEC

    monkeypatch.setattr(export, "all_models", lambda: [SPEC])
    return export, SPEC


def test_plan_then_bake_then_restore_is_byte_identical(tmp_path, label_card_only, monkeypatch):
    export, spec = label_card_only
    cache = tmp_path / "cache"
    assert export.cache_plan(cache / "plan.json") == 0
    plan = json.loads((cache / "plan.json").read_text())
    assert [(e["slug"], e["preset"]) for e in plan["entries"]] == [
        (spec.slug, p.id) for p in spec.presets]
    for entry in plan["entries"]:
        assert entry["pathname"] == (f"bd-bake-cache/v{bake_cache.SCHEMA}/{entry['key']}/"
                                     f"{entry['slug']}-{entry['preset']}.tar.gz")

    # Cold: every preset bakes and is staged under its planned key.
    first = tmp_path / "first"
    assert export.export_presets_only(first, cache) == 0
    bake = json.loads((cache / "bake.json").read_text())
    assert (bake["hits"], bake["misses"]) == (0, len(spec.presets))
    assert sorted(e["pathname"] for e in bake["store"]) == sorted(
        e["pathname"] for e in plan["entries"])

    # Warm: the restore step leaves each tarball at fetched/<key>.tar.gz.
    (cache / "store").rename(cache / "fetched")
    monkeypatch.setattr(export, "bake_preset", lambda *a: pytest.fail("a hit must not bake"))
    second = tmp_path / "second"
    (second / spec.slug).mkdir(parents=True)
    (second / spec.slug / "inlaid-stale.stl").write_text("stale part from an old colour set")
    assert export.export_presets_only(second, cache) == 0
    bake = json.loads((cache / "bake.json").read_text())
    assert (bake["hits"], bake["misses"], bake["store"]) == (len(spec.presets), 0, [])
    expected = sorted(p.name for p in (first / spec.slug).iterdir())
    assert sorted(p.name for p in (second / spec.slug).iterdir()) == expected
    for name in expected:
        assert (second / spec.slug / name).read_bytes() == (first / spec.slug / name).read_bytes()


def test_a_corrupt_tarball_bakes_that_preset(tmp_path, label_card_only):
    export, spec = label_card_only
    cache = tmp_path / "cache"
    export.cache_plan(cache / "plan.json")
    entry = json.loads((cache / "plan.json").read_text())["entries"][0]
    (cache / "fetched").mkdir()
    (cache / "fetched" / f"{entry['key']}.tar.gz").write_bytes(b"truncated")
    out = tmp_path / "out"
    assert export.export_presets_only(out, cache) == 0
    bake = json.loads((cache / "bake.json").read_text())
    assert (bake["hits"], bake["misses"]) == (0, len(spec.presets))
    assert (out / spec.slug / f"{entry['preset']}.stl").stat().st_size > 0


def test_an_uncovered_read_fails_the_bake_and_stages_nothing(tmp_path, label_card_only,
                                                             monkeypatch, capsys):
    export, spec = label_card_only
    audit = bake_cache.ReadAudit()
    monkeypatch.setattr(export, "AUDIT", audit)
    real = export.bake_preset

    def sneaky(spec_, preset, model_dir, unfit):
        (ROOT / "docs" / "bd-cli.md").read_text()  # not a key input
        return real(spec_, preset, model_dir, unfit)

    monkeypatch.setattr(export, "bake_preset", sneaky)
    cache = tmp_path / "cache"
    try:
        assert export.export_presets_only(tmp_path / "out", cache) == 1
    finally:
        audit.active = False
    err = capsys.readouterr().err
    for preset in spec.presets:  # every preset named, not just the first
        assert f"{spec.slug}/{preset.id}: docs/bd-cli.md" in err
    assert not (cache / "bake.json").exists()
    assert not (cache / "store").exists()
