"""tools/measure_step.py (pst-ff71): offline fixtures + upstream timing.

Offline tests build their own STEP/3MF fixtures in a temp dir. The one
``upstream`` test measures every measurable (brep/mesh) source record whose
mirrored file is on disk (reference/FETCH.md) and skips the rest; citation
(PDF) and archive (zip) records are excluded by construction.
"""

import json
import locale
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import ezdxf
import pytest
from build123d import Box, Cylinder, Mesher, Plane, Pos, export_step

ROOT = Path(__file__).resolve().parent.parent  # build123d/
sys.path.insert(0, str(ROOT / "tools"))

import measure_step as ms  # noqa: E402
from reference_pull import load_sources, local_path  # noqa: E402


def _step(tmp_path, shape, name="part.step"):
    path = tmp_path / name
    export_step(shape, str(path))
    return path


def _3mf(tmp_path, *shapes, name="part.3mf"):
    path = tmp_path / name
    mesher = Mesher()
    for shape in shapes:
        mesher.add_shape(shape)
    mesher.write(str(path))
    return path


def test_media_types():
    assert ms.media_type_of("a.STEP") == ms.media_type_of("b.stp") == ms.media_type_of("c.brep") == "brep"
    assert ms.media_type_of("a.3mf") == ms.media_type_of("a.stl") == "mesh"
    assert ms.media_type_of("drawing.pdf") == "citation"
    assert ms.media_type_of("bundle.zip") == "archive"
    with pytest.raises(ValueError):
        ms.media_type_of("notes.txt")
    # Every mirrored source resolves to a known media type.
    assert {ms.media_type_of(r["filename"]) for r in load_sources()} <= set(ms.MEDIA_TYPES.values())


def test_step_json_and_table(tmp_path):
    path = _step(tmp_path, Box(10, 20, 30))
    out = tmp_path / "m.json"
    assert ms.main([str(path), "--json", str(out)]) == 0
    m = json.loads(out.read_text())
    assert m["kind"] == "brep" and m["analytic"] == "ok" and m["solids"] == 1
    assert m["volume"] == pytest.approx(6000)
    assert m["bbox"]["size"] == pytest.approx([10, 20, 30])
    assert m["source"]["sha256"] == ms.sha256_of(path)
    assert m["levels"] == [-15.0, 15.0]  # planar faces normal to Z
    assert len(m["planes"]) == 6 and m["cylinders"] == []
    table = ms.format_table(m)
    for label in ("kind", "volume mm^3", "bbox size", "levels along Z"):
        assert label in table


def test_brep_cylinders_reported(tmp_path):
    path = _step(tmp_path, Pos(1, 2, 0) * Cylinder(3, 8) - Pos(1, 2, 0) * Cylinder(1.5, 8))
    m = ms.measure(path)
    radii = sorted(c["radius"] for c in m["cylinders"])
    assert radii == pytest.approx([1.5, 3])
    for cyl in m["cylinders"]:
        assert abs(cyl["axis"][2]) == pytest.approx(1)
        assert cyl["centre"][:2] == pytest.approx([1, 2])
    assert m["coaxial_radii"] == [1.5, 3.0]
    assert ms.measure(path, axis="X")["coaxial_radii"] == []


def test_3mf_mesh_only_fields_null(tmp_path):
    m = ms.measure(_3mf(tmp_path, Box(10, 10, 10)))
    assert m["kind"] == "mesh" and m["source"]["media_type"] == "mesh"
    assert m["analytic"] == ms.MESH_UNSUPPORTED
    for key in ("cylinders", "planes", "coaxial_radii", "levels"):
        assert m[key] is None
    assert m["volume"] == pytest.approx(1000, rel=1e-3)
    assert m["bbox"]["size"] == pytest.approx([10, 10, 10], abs=1e-3)
    assert m["solids"] == 1


def test_3mf_multi_object_compound(tmp_path):
    path = _3mf(tmp_path, Box(10, 10, 10), Pos(30, 0, 0) * Box(5, 5, 5))
    shape, kind = ms.load_shape(path)
    assert kind == "mesh" and len(shape.solids()) == 2
    m = ms.collect_measurements(shape, kind)
    assert m["solids"] == 2
    assert m["volume"] == pytest.approx(1125, rel=1e-3)


def test_mesh_without_objects_is_an_error(tmp_path, monkeypatch):
    path = _3mf(tmp_path, Box(1, 1, 1))
    monkeypatch.setattr(Mesher, "read", lambda self, name: [])
    with pytest.raises(ValueError, match="no objects"):
        ms.load_shape(path)


def test_stl_loads_as_mesh(tmp_path):
    path = tmp_path / "part.stl"
    mesher = Mesher()
    mesher.add_shape(Box(4, 5, 6))
    saved = locale.setlocale(locale.LC_ALL)
    mesher.write(str(path))
    locale.setlocale(locale.LC_ALL, saved)
    m = ms.measure(path)
    assert locale.setlocale(locale.LC_ALL) == saved  # load_shape restores lib3mf's reset
    assert m["kind"] == "mesh" and m["cylinders"] is None
    assert m["bbox"]["size"] == pytest.approx([4, 5, 6], abs=1e-3)


def test_section_dxf_svg_written(tmp_path):
    path = _step(tmp_path, Cylinder(5, 10) - Cylinder(2, 10))
    dxf, svg = tmp_path / "s.dxf", tmp_path / "s.svg"
    m = ms.measure(path, plane="XZ", offset=0, dxf=dxf, svg=svg)
    assert len(ezdxf.readfile(dxf).modelspace()) >= 1
    root = ET.parse(svg).getroot()
    assert root.tag.endswith("svg")
    assert len([el for el in root.iter() if el.tag.endswith("path")]) >= 1
    s = m["section"]
    assert s["plane"] == "XZ" and s["edges"]
    # Plane-local coords: u = world X, v = world Z (two 3 mm walls, 10 tall).
    assert s["bbox"]["min"] == pytest.approx([-5, -5]) and s["bbox"]["max"] == pytest.approx([5, 5])
    assert s["area"] == pytest.approx(2 * 3 * 10)


def test_section_offset_is_world_coordinate(tmp_path):
    path = _step(tmp_path, Pos(0, 50, 0) * Box(20, 10, 4))
    assert ms.measure(path, plane="XZ", offset=50)["section"]["area"] == pytest.approx(80)
    with pytest.raises(ValueError, match="empty"):
        ms.measure(path, plane="XZ", offset=0)


def test_citation_records_never_loaded(tmp_path, monkeypatch):
    """Walk every real source record the way the upstream timing test does:
    only brep/mesh records may reach load_shape; PDFs and zips never do."""
    records = load_sources()
    real_load_shape = ms.load_shape
    loaded = []
    monkeypatch.setattr(ms, "load_shape", lambda path: loaded.append(Path(path)) or (None, "brep"))
    selected = [r for r in records if ms.media_type_of(r["filename"]) in ms.MEASURABLE]
    for record in selected:
        ms.load_shape(local_path(record, record["current"], tmp_path))
    assert len(loaded) == len(selected)
    suffixes = {p.suffix.lower() for p in loaded}
    assert suffixes and not suffixes & {".pdf", ".zip"}
    inert = [r for r in records if ms.media_type_of(r["filename"]) not in ms.MEASURABLE]
    assert {ms.media_type_of(r["filename"]) for r in inert} == {"citation", "archive"}
    # The CLI refuses them before loading anything.
    loaded.clear()
    for suffix in (".pdf", ".zip"):
        f = tmp_path / f"x{suffix}"
        f.write_bytes(b"%PDF")
        assert ms.main([str(f)]) == 2
    assert loaded == []
    with pytest.raises(ValueError, match="not measurable"):
        real_load_shape(tmp_path / "x.pdf")


def test_cli_main_exit_codes(tmp_path, capsys):
    path = _step(tmp_path, Box(1, 2, 3))
    assert ms.main([str(path)]) == 0
    assert ms.main([str(tmp_path / "missing.step")]) == 2
    with pytest.raises(SystemExit) as exc:
        ms.main([str(path), "--dxf", str(tmp_path / "x.dxf")])  # needs --plane
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        ms.main([str(path), "--record"])  # needs an output
    # A file that is not a mirrored source cannot be recorded (no FK).
    art = tmp_path / "artifacts.json"
    rc = ms.main([str(path), "--json", str(tmp_path / "m.json"), "--record",
                  "--artifact-manifest", str(art)])
    assert rc == 1 and not art.exists()
    assert "cannot record" in capsys.readouterr().err


def test_record_writes_fk_and_licence(tmp_path):
    src = _step(tmp_path, Box(1, 1, 1))
    sha = ms.sha256_of(src)
    sources = tmp_path / "sources.json"
    sources.write_text(json.dumps({"schema": 2, "sources": [{
        "source_file_id": "g/part.step", "source_group_id": "g", "filename": "part.step",
        "licence": "Creative Commons — Attribution", "current": sha,
        "versions": [{"sha256": "0" * 64}, {"sha256": sha}]}]}))
    out = tmp_path / "reference" / "measured" / "part.json"
    out.parent.mkdir(parents=True)
    out.write_text("{}\n")
    art = tmp_path / "artifacts.json"
    [entry] = ms.record_artifacts([out], src, "cmd", None, manifest=art, sources=sources,
                                  today="2026-01-02", root=tmp_path)
    assert entry["file"] == "reference/measured/part.json"
    assert (entry["source_file_id"], entry["source_sha256"]) == ("g/part.step", sha)
    assert entry["licence_text"] == ms.LICENCE_TEXTS["Creative Commons — Attribution"]
    assert entry["sha256"] == ms.sha256_of(out) and entry["measured_on"] == "2026-01-02"
    assert ms.load_artifacts(art) == [entry]
    # Upsert by file: re-recording replaces, never duplicates.
    ms.record_artifacts([out], src, "cmd2", None, manifest=art, sources=sources, root=tmp_path)
    assert [a["command"] for a in ms.load_artifacts(art)] == ["cmd2"]
    # A licence without a committed text is refused.
    data = json.loads(sources.read_text())
    data["sources"][0]["licence"] = "Some Other Licence"
    sources.write_text(json.dumps(data))
    with pytest.raises(LookupError, match="no licence text"):
        ms.record_artifacts([out], src, "cmd", None, manifest=art, sources=sources, root=tmp_path)


# --- upstream: every measurable mirrored source in < 30 s --------------------

def _measurable_records():
    return [r for r in load_sources() if ms.media_type_of(r["filename"]) in ms.MEASURABLE]


@pytest.mark.upstream
@pytest.mark.parametrize("record", _measurable_records(), ids=lambda r: r["source_file_id"])
def test_runs_under_30s_on_every_measurable_source(record):
    path = local_path(record, record["current"])
    if not path.is_file():
        pytest.skip(f"{record['source_file_id']} not pulled (reference/FETCH.md)")
    start = time.monotonic()
    shape, kind = ms.load_shape(path)
    m = ms.collect_measurements(shape, kind)
    elapsed = time.monotonic() - start
    assert kind == ms.media_type_of(record["filename"])
    # Signed volume: some official STLs are wound inside-out (flush-big-coin-slot.stl
    # reports -167.77), so only a non-degenerate solid is required here.
    assert m["solids"] >= 1 and m["volume"] != 0
    assert elapsed < 30, f"{record['source_file_id']}: {elapsed:.1f}s"
