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
import subprocess
import sys
from pathlib import Path

import trimesh

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from holders.registry import all_models  # noqa: E402
from scripts.manifest import MANIFEST_PATH  # noqa: E402


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

    expected_files: set[Path] = set()
    for spec in specs:
        assert spec.presets, f"{spec.name}: app-listed models need presets"
        for preset in spec.presets:
            expected_files.add(target / spec.slug / f"{preset.id}.stl")
            expected_files.add(target / spec.slug / f"{preset.id}.glb")
            expected_files.add(target / spec.slug / f"{preset.id}.png")

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

    # Count: exactly 3 files (STL + GLB + PNG) per preset of every model.
    expected_count = sum(len(s.presets) for s in specs) * 3
    assert len(actual_files) == expected_count



def test_baked_count_matches_manifest():
    """Cross-check the emitter: manifest preset counts == registry counts,
    so CI bake coverage tracks what the app will list."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    registry = {s.slug: len(s.presets) for s in all_models() if not s.is_smoke}
    for model in manifest["models"]:
        assert model["slug"] in registry, f"manifest slug {model['slug']} not registered"
        assert len(model["presets"]) == registry[model["slug"]]
