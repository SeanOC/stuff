"""Review context, real GLB frame conversion, capped cuts and analytic goldens."""
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import trimesh
from PIL import Image
from build123d import Align, Box, Pos, export_gltf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from holders.registry import all_models, resolve_mount_fixtures, _validate_spec
from holders import cup_lid, spool_cradle
from scripts import thumbnail as th
from scripts.export import review_context, section_svg

SPECS = [s for s in all_models() if not s.is_smoke]


@pytest.fixture(scope="module")
def parts():
    return {s.slug: s.build(s.resolve_values()) for s in SPECS}


@pytest.fixture
def asymmetric_glb(tmp_path):
    # Origin-offset 1 x 2 x 3 box, with a unique tab on its -Z bed side.
    box = Pos(4, 7, 10) * Box(1, 2, 3, align=(Align.MIN,) * 3)
    tab = Pos(4, 7, 9.7) * Box(.3, .4, .5, align=(Align.MIN,) * 3)
    part = box.fuse(tab)
    glb = tmp_path / "asymmetric.glb"
    export_gltf(part, str(glb), binary=True)
    mesh = trimesh.load(glb, force="scene").to_geometry()
    return glb, mesh


def test_frame_transform_asymmetric_fixture(asymmetric_glb, monkeypatch):
    _, mesh = asymmetric_glb
    np.testing.assert_allclose(th.model_to_glb_point((4, 7, 10)), (.004, .010, -.007))
    np.testing.assert_allclose(th.model_to_glb_vector((1, 2, 3)), (1, 3, -2))
    np.testing.assert_allclose(mesh.bounds, [[.004, .0097, -.009], [.005, .013, -.007]], atol=1e-8)
    cut = th._section_mesh(mesh, th.PlaneSpec((4.5, 7, 10), (1, 0, 0), "offset"))
    assert len(cut.faces) and cut.is_watertight
    assert cut.bounds[1, 0] == pytest.approx(.0045)
    assert cut.volume == pytest.approx((.5 * 2 * 3 + .3 * .4 * .3) / 1e9, rel=1e-5)
    # Model +Y becomes GLB -Z; the retained half must land on the +Z side.
    y_cut = th._section_mesh(mesh, th.PlaneSpec((4, 8, 10), (0, 1, 0), "Y offset"))
    assert len(y_cut.faces) and y_cut.is_watertight
    assert y_cut.bounds[0, 2] == pytest.approx(-.008)
    assert y_cut.volume == pytest.approx((1 * 1 * 3 + .3 * .4 * .3) / 1e9, rel=1e-5)
    captured = {}
    def capture(*args, **kwargs):
        captured.update(kwargs)
    monkeypatch.setattr(th, "_render_view", capture)
    th._underside_tile(mesh, (0, 0, 1), th._BASE_COLOR, 64)
    np.testing.assert_array_equal(captured["view_dir"], (0, -1, 0))
    th._underside_tile(mesh, (0, 1, 0), th._BASE_COLOR, 64)
    np.testing.assert_array_equal(captured["view_dir"], (0, 0, 1))


def test_section_tile_cap_watertight(asymmetric_glb):
    _, mesh = asymmetric_glb
    plane = th.PlaneSpec((4.5, 7, 10), (1, 0, 0), "offset")
    cut = th._section_mesh(mesh, plane)
    assert cut.is_watertight and cut.volume > 0
    cap = np.all(np.isclose(cut.vertices[cut.faces, 0], .0045), axis=1)
    assert cap.any()
    tile = th._section_tile(mesh, plane, th._BASE_COLOR, 64)
    # The cut face's orange tint is distinct from the blue-grey material.
    assert np.any((tile[:, :, 0] > tile[:, :, 2]) & (tile[:, :, 3] > 0))


def test_resolve_mount_fixtures_mounted():
    spec = spool_cradle.SPEC
    fx = resolve_mount_fixtures(spec, spec.mounts[0], spec.resolve_values())
    assert fx.cutters and fx.seat_locs


def test_resolve_mount_fixtures_unmounted():
    spec = cup_lid.SPEC
    assert resolve_mount_fixtures(spec, "", spec.resolve_values()) is None


def test_resolve_mount_fixtures_absent_style():
    # holder_spool_cradle selects one of its two mounts per mount_style.
    spec = spool_cradle.SPEC
    oc = spec.resolve_values({"mount_style": "openconnect"})
    assert resolve_mount_fixtures(spec, "openconnect-slot", spec.resolve_values()) is None
    assert resolve_mount_fixtures(spec, "multibuild-multiconnect-channel", oc) is None
    assert resolve_mount_fixtures(spec, "openconnect-slot", oc).cutters


def test_default_plane_mounted_model(parts):
    candidates = ((s, resolve_mount_fixtures(s, mount, s.resolve_values()))
                  for s in SPECS if not s.review_sections for mount in s.mounts)
    # A declared mount may be inactive for the default values (the cartridge
    # holder defaults to positive snaps, not its optional receiver fixtures).
    spec, fx = next((s, fx) for s, fx in candidates if fx is not None)
    ctx = review_context(spec, spec.resolve_values(), parts[spec.slug])
    assert len(ctx.sections) == 1
    assert ctx.sections[0].origin == tuple(fx.seat_locs[0].position)
    np.testing.assert_array_equal(ctx.sections[0].normal, np.cross(fx.face_normal, fx.entry_axis))


def test_default_plane_no_mount_model(parts):
    spec = cup_lid.SPEC
    ctx = review_context(spec, spec.resolve_values(), parts[spec.slug])
    assert ctx.sections[0].origin == tuple(parts[spec.slug].bounding_box().center())
    assert ctx.sections[0].normal == (1, 0, 0)


def test_declared_plane_used(parts):
    spec = spool_cradle.SPEC
    ctx = review_context(spec, spec.resolve_values(), parts[spec.slug])
    assert ctx.sections is spec.review_sections
    assert ctx.sections[0].origin == (0, spool_cradle.dimensions()["center_y"], 0)


def test_five_tiles_dimensions(asymmetric_glb, tmp_path):
    glb, _ = asymmetric_glb
    png = tmp_path / "review.png"
    ctx = th.ReviewContext("fixture", (0, 0, 1),
                           (th.PlaneSpec((4.5, 7, 10), (1, 0, 0), "offset"),
                            th.PlaneSpec((999, 0, 0), (1, 0, 0), "unused")), ())
    th.render_review(glb, png, ctx=ctx, res=64)
    with Image.open(png) as img:
        assert img.size == (320, 112)
        for i in range(5):
            assert np.any(np.asarray(img)[28:92, i*64:(i+1)*64] < 200)


def test_legacy_two_arg_call_still_three_tiles(asymmetric_glb, tmp_path):
    glb, _ = asymmetric_glb
    png = tmp_path / "legacy.png"
    th.render_review(glb, png)
    with Image.open(png) as img:
        assert img.size == (th._RES*3, th._RES)
        assert img.mode == "RGBA"


@pytest.mark.parametrize("plane, error", [
    (th.PlaneSpec((0, 0, 0), (0, 0, 0), "zero"), "non-zero"),
    (th.PlaneSpec((0, 0, 0), (1, 0, 0), ""), "non-empty"),
    (th.PlaneSpec((float("nan"), 0, 0), (1, 0, 0), "bad"), "finite"),
])
def test_validate_spec_rejects_zero_normal(plane, error):
    assert error in _validate_spec(replace(cup_lid.SPEC, review_sections=(plane,)))


def test_context_requires_resolved_sections():
    with pytest.raises(ValueError, match="resolved section"):
        th.ReviewContext("empty", (0, 0, 1), (), ())


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.slug)
def test_section_golden(spec, parts, file_regression):
    part = parts[spec.slug]
    plane = review_context(spec, spec.resolve_values(), part).sections[0]
    file_regression.check(section_svg(part, plane), extension=".svg",
                          fullpath=ROOT / "docs/renders/sections" / f"{spec.slug}.svg")


def test_export_all_commits_only_non_smoke_reviews(tmp_path, monkeypatch):
    from scripts import export as exporter
    spec = replace(cup_lid.SPEC, build=lambda values: Box(10, 20, 30))
    smoke = replace(spec, name="smoke_box", tags=("smoke",))
    monkeypatch.setattr(exporter, "OUT", tmp_path / "out")
    monkeypatch.setattr(exporter, "all_models", lambda: [spec, smoke])
    seen = []
    def render(glb, png, *, ctx):
        seen.append(ctx)
        th.render_review(glb, png, ctx=ctx, res=64)
    monkeypatch.setattr(exporter, "render_review", render)
    assert exporter.export_all(commit_review=True) == 0
    assert [c.slug for c in seen] == [spec.slug, smoke.slug]
    assert seen[0].print_orientation == spec.print_orientation
    assert seen[0].mounts == spec.mounts
    review = tmp_path / "docs/renders/review" / f"{spec.slug}.png"
    assert review.read_bytes() == (tmp_path / "out" / f"{spec.name}.png").read_bytes()
    assert list(review.parent.glob("*.png")) == [review]
    sections = tmp_path / "docs/renders/sections"
    assert [p.name for p in sections.glob("*.svg")] == [f"{spec.slug}.svg"]
    with Image.open(review) as image:
        assert image.size == (320, 112)
