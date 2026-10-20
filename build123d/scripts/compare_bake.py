"""Offline comparison of a LOCAL scripts/export.py --presets-only directory.

Never use the bd123-models artifact: it contains defaults, not app presets.
Compare structure/semantics and scalar mesh metrics, NOT byte identity or
triangle-multiset equality: identical OCCT 8 builds can retriangulate (see
docs/bake-repeatability.md). The shared welded metrics are not exact coordinate
comparisons. Raw oriented-triangle/vertex digests are diagnostic only, and a
scalar PASS is not proof of surface equivalence; inspect changed connectivity.
PNG pixels and GLB binary attribute values are outside this numerical gate.
"""
import argparse
from collections import Counter
import hashlib
import json
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.bake_repeatability import _metrics, _oriented_triangles, _rows
from scripts.baseline_common import load_waivers, read_baseline, report


def glb_structure(path):
    data = path.read_bytes()
    if len(data) < 20 or struct.unpack_from("<4sII", data) != (b"glTF", 2, len(data)):
        raise ValueError(f"invalid GLB: {path}")
    length, kind = struct.unpack_from("<I4s", data, 12)
    if kind != b"JSON" or 20 + length > len(data):
        raise ValueError(f"invalid GLB JSON chunk: {path}")
    doc = json.loads(data[20:20 + length])
    accessors = doc.pop("accessors", [])
    for mesh in doc.get("meshes", []):
        groups = {}
        for primitive in mesh.pop("primitives", []):
            # OCCT emits a primitive per face: some presets have 40,000
            # accessors. Group by material/mode/attribute schema, retaining
            # count distributions and aggregate bounds without pinning face
            # order or committing tens of MB of duplicated layout metadata.
            refs = dict(primitive.get("attributes", {}))
            if "indices" in primitive:
                refs["indices"] = primitive["indices"]
            descriptors = {}
            for role, index in refs.items():
                accessor = accessors[index]
                descriptors[role] = {k: v for k, v in accessor.items()
                                     if k not in ("bufferView", "byteOffset", "count", "min", "max")}
            schema = {k: v for k, v in primitive.items() if k not in ("attributes", "indices")}
            schema["accessors"] = descriptors
            key = json.dumps(schema, sort_keys=True)
            group = groups.setdefault(key, {"schema": schema, "primitives": 0, "attributes": {}})
            group["primitives"] += 1
            for role, index in refs.items():
                accessor = accessors[index]
                summary = group["attributes"].setdefault(role, {"count": 0, "count_inventory": {}})
                count = accessor["count"]
                summary["count"] += count
                inventory = summary["count_inventory"]
                inventory[str(count)] = inventory.get(str(count), 0) + 1
                for bound, operation in (("min", min), ("max", max)):
                    if bound in accessor:
                        previous = summary.get(bound, accessor[bound])
                        summary[bound] = [operation(a, b) for a, b in zip(previous, accessor[bound])]
        mesh["primitive_groups"] = [groups[key] for key in sorted(groups)]
    # Buffer packing and the generating engine's label are not scene semantics.
    doc.get("asset", {}).pop("generator", None)
    doc.pop("buffers", None)
    doc.pop("bufferViews", None)
    return doc


def xml_structure(element):
    tag = element.tag.rsplit("}", 1)[-1]
    if tag == "mesh":
        vertices = [[float(v.attrib[axis]) for axis in ("x", "y", "z")]
                    for v in element.findall("./{*}vertices/{*}vertex")]
        triangles = [[int(t.attrib[axis]) for axis in ("v1", "v2", "v3")]
                     for t in element.findall("./{*}triangles/{*}triangle")]
        if not vertices or not triangles:
            raise ValueError("empty 3MF mesh")
        metrics = _metrics(trimesh.Trimesh(vertices=vertices, faces=triangles, process=False))
        # Retain per-triangle material assignments independently of face ordering.
        properties = dict(Counter(
            json.dumps({k: v for k, v in t.attrib.items() if k not in ("v1", "v2", "v3")},
                       sort_keys=True)
            for t in element.findall("./{*}triangles/{*}triangle")))
        return {"tag": element.tag, "metrics": metrics, "properties": properties}
    attrs = dict(element.attrib)
    for key in attrs:
        if key.rsplit("}", 1)[-1] == "transform":
            attrs[key] = [float(v) for v in attrs[key].split()]
    return {"tag": element.tag, "attributes": attrs,
            "text": (element.text or "").strip(),
            "children": [xml_structure(child) for child in element]}


def three_mf_structure(path):
    members = {}
    with zipfile.ZipFile(path) as package:
        names = package.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate ZIP members: {path}")
        for name in sorted(names):
            data = package.read(name)
            if name.endswith(".config") and data.lstrip().startswith(b"{"):
                members[name] = json.loads(data)
            else:
                # Exported 3MFs contain only XML and JSON: unknown payloads fail
                # rather than disappearing silently from the structure baseline.
                members[name] = xml_structure(ET.fromstring(data))
    if "3D/3dmodel.model" not in members:
        raise ValueError(f"missing 3MF model: {path}")
    return members


def collect(directory):
    rows, diagnostics = {}, {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(directory).as_posix()
        if path.suffix == ".stl":
            raw = trimesh.load_mesh(path, process=False)
            rows[name] = _metrics(raw)
            diagnostics[name] = {
                "oriented_triangles": hashlib.sha256(
                    _oriented_triangles(raw).astype("<f8").tobytes()).hexdigest(),
                "vertex_coordinates": hashlib.sha256(
                    np.unique(_rows(raw.vertices), axis=0).astype("<f8").tobytes()).hexdigest(),
            }
        elif path.suffix == ".glb":
            rows[name] = glb_structure(path)
        elif path.suffix == ".3mf":
            rows[name] = three_mf_structure(path)
        elif path.suffix == ".png":
            data = path.read_bytes()
            if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError(f"invalid PNG: {path}")
            rows[name] = {"dimensions": list(struct.unpack_from(">II", data, 16))}
        else:
            raise ValueError(f"unexpected bake file: {path}")
    if not rows:
        raise ValueError(f"empty or missing bake directory: {directory}")
    return rows, diagnostics


def classifications(before, after):
    return {name: ("same-oriented-triangles" if before[name]["oriented_triangles"] ==
                   after[name]["oriented_triangles"] else
                   "connectivity-or-winding" if before[name]["vertex_coordinates"] ==
                   after[name]["vertex_coordinates"] else "vertex-coordinates")
            for name in sorted(before.keys() & after.keys())}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        baseline = read_baseline("bake")
        rows, diagnostic = collect(args.directory)
        for name, classification in classifications(baseline["diagnostics"], diagnostic).items():
            if classification != "same-oriented-triangles":
                print(f"{name}: DIAGNOSTIC {classification}; inspect surfaces/BREP/audit evidence")
        return report("bake", baseline["rows"], rows, load_waivers())
    except (ValueError, OSError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"bake: ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
