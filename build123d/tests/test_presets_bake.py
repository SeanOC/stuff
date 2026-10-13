"""--presets-only bake contract (bead pst-pa1o).

Builds every preset of every app-listed (non-smoke) model via
scripts/export.py --presets-only and asserts the AC:

  - every registered app-listed model appears (no silent skips),
  - every preset of every such model gets STL + GLB + PNG thumbnail,
  - paths are deterministic and safe: <target>/<slug>/<preset-id>.{stl,glb,png},
  - no other files are written (no leftovers),
  - a missing expected output fails the test.

The PNG is the gallery thumbnail (bead pst-1vi5): rendered from the same
built part as the GLB/STL so the listing card can never drift from the
detail-view geometry.
"""
import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest
import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from holders.registry import (all_models, resolve_colour_parts,  # noqa: E402
                              resolve_preview_parts)
from scripts.manifest import MANIFEST_PATH  # noqa: E402


# Bakes every app-listed preset (~30 s) -> bd123 `audit` job (pst-24tr6).
@pytest.mark.audit
def test_presets_only_bakes_every_app_listed_preset(tmp_path):
    target = tmp_path / "bake"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "export.py"),
         "--presets-only", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"export failed:\n{proc.stdout}\n{proc.stderr}"

    specs = [s for s in all_models() if not s.is_smoke]
    assert specs, "expected app-listed models"

    # Per-filament STLs are named after the colour parts (pst-tl4ac.1).
    colour_names = {(s.slug, p.id): [name for name, _, _ in resolve_colour_parts(s, p.values)]
                    for s in specs if s.is_multi_colour for p in s.presets}
    expected_files: set[Path] = set()
    for spec in specs:
        assert spec.presets, f"{spec.name}: app-listed models need presets"
        for preset in spec.presets:
            expected_files.add(target / spec.slug / f"{preset.id}.stl")
            expected_files.add(target / spec.slug / f"{preset.id}.glb")
            expected_files.add(target / spec.slug / f"{preset.id}.png")
            if spec.is_multi_colour:  # gated extras (labels L2): 3MF + one STL per filament
                expected_files.add(target / spec.slug / f"{preset.id}.3mf")
                for name in colour_names[spec.slug, preset.id]:
                    expected_files.add(target / spec.slug / f"{preset.id}-{name}.stl")

    # Every expected artifact exists and is a valid mesh / non-empty PNG.
    for path in sorted(expected_files):
        assert path.exists(), f"missing baked artifact: {path}"
        if path.suffix == ".stl":
            mesh = trimesh.load_mesh(path)
            assert mesh.is_watertight, f"{path.name}: baked STL not watertight"
            assert mesh.volume > 0, f"{path.name}: baked STL zero volume"
        if path.suffix == ".png":
            # PNG signature + non-trivial size: a real render, not a stub.
            assert path.stat().st_size > 1000, f"{path.name}: thumbnail too small"
            assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", (
                f"{path.name}: not a PNG"
            )

    # Nothing else was written — deterministic path set, no skips/extras.
    actual_files = {p for p in target.rglob("*") if p.is_file()}
    assert actual_files == expected_files, (
        "unexpected/missing files in bake target: "
        f"extra={sorted(map(str, actual_files - expected_files))}, "
        f"missing={sorted(map(str, expected_files - actual_files))}"
    )

    # Viewer GLB materials (pst-5b83s): one per preview colour part; a preset
    # whose preview hook declines (raised, single colour) keeps the plain,
    # material-less GLB.
    for spec in specs:
        for preset in spec.presets:
            glb = (target / spec.slug / f"{preset.id}.glb").read_bytes()
            (length,) = struct.unpack("<I", glb[12:16])
            materials = json.loads(glb[20:20 + length]).get("materials", [])
            parts = resolve_preview_parts(spec, preset.values)
            assert len(materials) == (0 if parts is None else len(parts)), \
                f"{spec.slug}/{preset.id}"

    # Count: STL + GLB + PNG per preset; multi-colour adds the 3MF + one STL per part.
    expected_count = sum(4 + len(colour_names[s.slug, p.id]) if s.is_multi_colour else 3
                         for s in specs for p in s.presets)
    assert len(actual_files) == expected_count



def test_baked_count_matches_manifest():
    """Cross-check the emitter: manifest preset counts == registry counts,
    so CI bake coverage tracks what the app will list."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    registry = {s.slug: len(s.presets) for s in all_models() if not s.is_smoke}
    for model in manifest["models"]:
        assert model["slug"] in registry, f"manifest slug {model['slug']} not registered"
        assert len(model["presets"]) == registry[model["slug"]]


# sha256 of the label card's bake on origin/main 6db43491, BEFORE the
# per-part STL names (pst-tl4ac.1). The generalisation only renames the
# inlaid preset's filament-2 STL (-text -> -inlay, its colour part name);
# every byte stays the same. A deliberate OCCT / lib3mf bump re-pins these.
LABEL_CARD_BAKE_SHA256 = {
    "inlaid-base.stl": "b7b7a2b6de634c64849fb2dabe278755eea7c87f830073847685ce3595e57af0",
    "inlaid-inlay.stl": "4b93c5af55cb64c06988f0d92ff410bc900b8ab25ce6f4d65ebe49ada54703b8",
    "inlaid.3mf": "cbd8d53e918cacd3ebd0c9f6770d1f73c6dec7a0815e01dc111092686ef2bd6b",
    "inlaid.glb": "f41f6ed78d27ae30e98196ec6b51f587c8a81e304f54adca3c20d2bddf4b27b8",
    "raised-base.stl": "b1d00fc5feb7cd875c933f5e1004fe2111fafbec2ca00be03517a565b979041c",
    "raised-text.stl": "5b59e46e2dc89e552bc24141432efec9330975e99e08ce45bf24e342bb722517",
    "raised.3mf": "c4f858b69b8934f398962764d542a0d24fb1727320a4c248c576c57555c57881",
    "raised.glb": "803ddae6a192e134963936c47246f9173d3f049b21426f8c57cdd1b0006bc2c2",
}


def test_label_card_bake_bytes_survive_the_part_name_generalisation(tmp_path, monkeypatch):
    import hashlib

    import scripts.export as export
    from holders.label_card import SPEC

    monkeypatch.setattr(export, "all_models", lambda: [SPEC])
    assert export.export_presets_only(tmp_path) == 0
    for name, digest in LABEL_CARD_BAKE_SHA256.items():
        data = (tmp_path / SPEC.slug / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, name
    assert not (tmp_path / SPEC.slug / "inlaid-text.stl").exists()
