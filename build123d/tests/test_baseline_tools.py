"""Small real fixture pairs exercise the comparators without CI artifacts."""
import copy
import json
import struct
from types import SimpleNamespace
import zipfile

import pytest
import trimesh

from scripts import compare_audit_rows as audit
from scripts import compare_bake as bake
from scripts import geometry_baseline as geometry
from scripts import rebaseline
from scripts.baseline_common import compare, load_waivers, write_json


def test_geometry_fixture_pair_and_field_modes():
    from build123d import Box, Location
    spec = SimpleNamespace(
        resolve_values=lambda values: values,
        build=lambda values: Box(values["width"], 3, 4),
        print_frame=lambda values: Location((0, 0, 10)),
    )
    preset = SimpleNamespace(values={"width": 2})
    row = geometry.measure(spec, preset)
    assert len(row["containment"]) == 125
    assert all(row["containment"])
    assert row["solids"] == 1 and row["faces"] == 6
    assert row["print_bounds"][0][2] - row["raw_bounds"][0][2] == 10
    assert not compare("geometry", {"box/default": row}, {"box/default": row})[0]
    changed = copy.deepcopy(row)
    changed["volume"] += row["volume"] * 0.5e-6  # relative, not absolute
    changed["print_bounds"][0][0] += 0.5e-6
    assert not compare("geometry", row, changed)[0]
    changed["print_bounds"][0][0] += 2e-6
    changed["solids"] += 1
    changed["containment"][0] = False
    failures, _ = compare("geometry", {"box/default": row}, {"box/default": changed})
    assert any("/box~1default/print_bounds/0/0" in line for line in failures)
    assert any("/solids:" in line and "exact" in line for line in failures)
    assert any("/containment/0:" in line and "exact" in line for line in failures)
    assert compare("audit-rows", {"volume": 100000.0}, {"volume": 100000.001})[0]
    assert compare("bake", {"volume_mm3": 100000.0}, {"volume_mm3": 100000.001})[0]


def test_missing_extra_fields_and_reasoned_waivers(tmp_path):
    failures, _ = compare("geometry", {"a/b": {"faces": 1}}, {"extra": {}})
    assert failures == ["/a~1b: missing", "/extra: unexpected"]
    waiver = {"kind": "geometry", "path": "/a~1b", "reason": "fixture", "bead": "pst-test"}
    assert not compare("geometry", {"a/b": {}}, {}, [waiver])[0]
    assert "pst-test" in compare("geometry", {"a/b": {}}, {}, [waiver])[1][0]
    path = tmp_path / "waivers.json"
    write_json(path, {"waivers": [waiver]})
    assert load_waivers(path) == [waiver]
    del waiver["reason"]
    write_json(path, {"waivers": [waiver]})
    with pytest.raises(ValueError, match="reason"):
        load_waivers(path)
    assert compare("geometry", {"faces": 6}, {"faces": 6.00000001})[0]


def test_geometry_command_fixture_pair(monkeypatch, capsys):
    expected = {"box/default": {"volume": 24.0, "solids": 1}}
    monkeypatch.setattr(geometry, "read_baseline", lambda kind: {"rows": expected})
    monkeypatch.setattr(geometry, "load_waivers", lambda: [])
    monkeypatch.setattr(geometry, "collect", lambda: expected)
    assert geometry.main([]) == 0
    monkeypatch.setattr(geometry, "collect", lambda: {"box/default": {"volume": 25.0, "solids": 1}})
    assert geometry.main([]) == 1
    assert "/box~1default/volume: 24.0 -> 25.0 (relative 1e-06)" in capsys.readouterr().out


def test_deterministic_json_and_nonfinite(tmp_path):
    path = tmp_path / "baseline.json"
    write_json(path, {"z": -0.0, "a": 1.23456789012})
    before = path.read_bytes()
    write_json(path, {"a": 1.23456789012, "z": 0.0})
    assert path.read_bytes() == before
    assert b"1.234567890" in before and b"0.000000000" in before
    with pytest.raises(ValueError, match="non-finite"):
        write_json(path, {"x": float("nan")})


def make_bake(directory, width=2):
    directory.mkdir()
    mesh = trimesh.creation.box(extents=(width, 3, 4))
    mesh.export(directory / "box.stl")
    (directory / "box.glb").write_bytes(mesh.scene().export(file_type="glb"))
    (directory / "box.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I4sII", 13, b"IHDR", 100, 100))
    with zipfile.ZipFile(directory / "box.3mf", "w") as package:
        package.writestr("3D/3dmodel.model", """<model unit="millimeter">
<resources><object id="1" name="base"><mesh>
<vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/>
<vertex x="0" y="1" z="0"/><vertex x="0" y="0" z="1"/></vertices>
<triangles><triangle v1="0" v2="2" v3="1"/><triangle v1="0" v2="1" v3="3"/>
<triangle v1="0" v2="3" v3="2"/><triangle v1="1" v2="2" v3="3"/></triangles>
</mesh></object><object id="2"><components><component objectid="1"
transform="1 0 0 0 1 0 0 0 1 0 0 0"/></components></object></resources>
<build><item objectid="2"/></build></model>""")
        package.writestr("Metadata/model_settings.config",
                         '<config><part id="1"><metadata key="extruder" value="1"/></part></config>')
        package.writestr("Metadata/project_settings.config", '{"printer_model":"fixture"}')


def test_bake_fixture_pair_and_readable_volume_diff(tmp_path, monkeypatch, capsys):
    make_bake(tmp_path / "before")
    make_bake(tmp_path / "after")
    before, diagnostic = bake.collect(tmp_path / "before")
    after, other = bake.collect(tmp_path / "after")
    assert not compare("bake", before, after)[0]
    assert set(bake.classifications(diagnostic, other).values()) == {"same-oriented-triangles"}
    monkeypatch.setattr(bake, "read_baseline", lambda kind: {
        "rows": before, "diagnostics": diagnostic})
    monkeypatch.setattr(bake, "load_waivers", lambda: [])
    assert bake.main([str(tmp_path / "after")]) == 0
    trimesh.creation.box(extents=(2.1, 3, 4)).export(tmp_path / "after/box.stl")
    assert bake.main([str(tmp_path / "after")]) == 1
    output = capsys.readouterr().out
    assert "/box.stl/volume_mm3:" in output and "absolute" in output
    assert "DIAGNOSTIC vertex-coordinates" in output
    (tmp_path / "after/box.glb").unlink()
    assert bake.main([str(tmp_path / "after")]) == 1
    assert "/box.glb: missing" in capsys.readouterr().out


def test_glb_repacking_is_ignored_but_primitive_count_is_exact(tmp_path):
    make_bake(tmp_path / "bake")
    path = tmp_path / "bake/box.glb"
    expected = bake.glb_structure(path)
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(data[20:20 + length])
    rest = data[20 + length:]

    def save():
        chunk = json.dumps(doc).encode()
        chunk += b" " * (-len(chunk) % 4)
        path.write_bytes(struct.pack("<4sII", b"glTF", 2, 20 + len(chunk) + len(rest))
                         + struct.pack("<I4s", len(chunk), b"JSON") + chunk + rest)

    last = len(doc["accessors"]) - 1
    doc["accessors"].reverse()
    for mesh in doc["meshes"]:
        for primitive in mesh["primitives"]:
            primitive["attributes"] = {k: last - v for k, v in primitive["attributes"].items()}
            primitive["indices"] = last - primitive["indices"]
    save()
    assert bake.glb_structure(path) == expected
    doc["meshes"][0]["primitives"] *= 2
    save()
    failures, _ = compare("bake", expected, bake.glb_structure(path))
    assert any("/primitives:" in failure and "exact" in failure for failure in failures)


@pytest.mark.parametrize("field", ["material", "transform", "filament", "profile", "component"])
def test_bake_semantics_are_not_waived_by_equal_stl(tmp_path, field):
    make_bake(tmp_path / "bake")
    rows, _ = bake.collect(tmp_path / "bake")
    changed = copy.deepcopy(rows)
    if field == "material":
        changed["box.glb"]["materials"] = [{"pbrMetallicRoughness": {"metallicFactor": 1.0}}]
    elif field == "transform":
        changed["box.glb"]["nodes"][0]["translation"] = [1.0, 0.0, 0.0]
    elif field == "profile":
        changed["box.3mf"]["Metadata/project_settings.config"]["printer_model"] = "other"
    elif field == "filament":
        changed["box.3mf"]["Metadata/model_settings.config"]["children"][0]["children"][0][
            "attributes"]["value"] = "2"
    else:
        changed["box.3mf"]["3D/3dmodel.model"]["children"][0]["children"][1]["children"][0][
            "children"][0]["attributes"]["objectid"] = "3"
    assert compare("bake", rows, changed)[0]


def audit_fixture(directory, group=None, wall=1.6, measurement=True):
    directory.mkdir(parents=True, exist_ok=True)
    records = [
        {"kind": "session", "markexpr": "audit" if group is None else "audit_full",
         "group": group, "started_at": "ignored"},
        {"kind": "collection", "audited": 1, "collected": 1},
        {"kind": "outcome", "nodeid": f"tests/test_box.py::test_box[{group}]",
         "when": "call", "outcome": "passed", "xfail": False, "duration_s": 1.0},
    ]
    if measurement:
        records.append({"kind": "measurement", "nodeid": records[2]["nodeid"], "name": "box",
                        "fields": {"wall": wall, "inventory": {"exposed": 2}, "ok": True}})
    (directory / "rows.gw0.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return records


def test_audit_fixture_pair_diff_missing_row_and_scope(tmp_path, monkeypatch, capsys):
    audit_fixture(tmp_path / "before/audit")
    audit_fixture(tmp_path / "before/full", group=1)
    audit_fixture(tmp_path / "after/audit")
    audit_fixture(tmp_path / "after/full", group=1)
    rows, scope = audit.collect(tmp_path / "before")
    baseline = {"header": {"job_scope": scope}, "rows": rows}
    monkeypatch.setattr(audit, "read_baseline", lambda kind: baseline)
    monkeypatch.setattr(audit, "load_waivers", lambda: [])
    assert audit.main([str(tmp_path / "after")]) == 0
    audit_fixture(tmp_path / "after/audit", wall=1.599)
    assert audit.main([str(tmp_path / "after")]) == 1
    output = capsys.readouterr().out
    assert "/wall: 1.6 -> 1.599 (absolute 1e-06)" in output
    audit_fixture(tmp_path / "after/audit", measurement=False)
    assert audit.main([str(tmp_path / "after")]) == 1
    assert "missing" in capsys.readouterr().out
    assert audit.main([str(tmp_path / "after/audit")]) == 2
    assert "NOT COMPARABLE" in capsys.readouterr().out
    failures, _ = compare("audit-rows", rows, audit.collect(tmp_path / "after")[0])
    missing = failures[0].removesuffix(": missing")
    monkeypatch.setattr(audit, "load_waivers", lambda: [{
        "kind": "audit-rows", "path": missing, "reason": "fixture", "bead": "pst-fixture"}])
    assert audit.main([str(tmp_path / "after")]) == 0
    assert "WAIVED" in capsys.readouterr().out


def test_audit_truncation_and_duplicate_measurements_fail(tmp_path):
    records = audit_fixture(tmp_path)
    path = tmp_path / "rows.gw0.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records + [records[-1]]))
    with pytest.raises(ValueError, match="duplicate audit row"):
        audit.collect(tmp_path)
    records.pop(2)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    with pytest.raises(ValueError, match="incomplete outcome"):
        audit.collect(tmp_path)
    records = audit_fixture(tmp_path)
    records[2]["outcome"] = "failed"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    with pytest.raises(ValueError, match="failed test outcomes"):
        audit.collect(tmp_path)


def test_rebaseline_requires_reason_and_provenance():
    with pytest.raises(SystemExit) as error:
        rebaseline.main(["--audit-rows", "absent", "--audit-source", "run fixture"])
    assert error.value.code == 2
    with pytest.raises(SystemExit):
        rebaseline.main(["--why", " ", "--audit-rows", "absent", "--audit-source", "run fixture"])


def test_rebaseline_rejects_incomplete_preset_bake(monkeypatch):
    spec = SimpleNamespace(slug="box", is_multi_colour=False)
    preset = SimpleNamespace(id="default")
    monkeypatch.setattr(geometry, "preset_specs", lambda: [(spec, preset)])
    rows = {f"box/default.{suffix}": {} for suffix in ("stl", "glb", "png")}
    rebaseline.validate_inventory(rows)
    del rows["box/default.glb"]
    with pytest.raises(ValueError, match="box/default.glb"):
        rebaseline.validate_inventory(rows)
