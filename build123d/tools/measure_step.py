"""Measure an official upstream CAD file and (optionally) record the result.

Reads one STEP/BREP (analytic B-rep) or 3MF/STL (mesh) file and reports its
bounding box, volume and solid count; for B-rep input also every cylindrical
face (radius, axis, centre) and every planar face above an area threshold.
``--plane`` adds a planar section, written as DXF/SVG in the plane's local
(u, v) coordinates, with its edge list in the JSON so derived dimensions
(thread pitch, band heights, across-flats) stay traceable to the file.

    uv run tools/measure_step.py <file.step|.brep|.3mf|.stl> [--axis Z]
        [--plane XY|XZ|YZ --z OFFSET] [--json out.json]
        [--dxf out.dxf] [--svg out.svg] [--record]

``--z`` is the WORLD coordinate along the plane's normal axis (XY -> Z,
XZ -> Y, YZ -> X). ``--record`` appends/refreshes one entry per written output
in ``reference/artifact-manifest.json``; the input must be a verified file in
``reference/source-manifest.json`` (its sha256 selects the exact version, the
foreign key ``(source_file_id, source_sha256)``). Provenance policy:
docs/provenance.md. Upstream originals are never committed (reference/FETCH.md).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import locale
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # build123d/
SOURCE_MANIFEST = ROOT / "reference" / "source-manifest.json"
ARTIFACT_MANIFEST = ROOT / "reference" / "artifact-manifest.json"
ARTIFACT_SCHEMA = 1
TOOL_VERSION = "measure_step/1"
PRECISION = 4
MIN_PLANE_AREA = 1.0  # mm^2; smaller planar faces are thread/facet noise
MESH_UNSUPPORTED = "unsupported for mesh input"

# Source-manifest licence string -> the licence text committed next to the
# artefacts. --record refuses a source whose licence has no text here.
LICENCE_TEXTS = {
    "Multiboard Licence (non-commercial)": "reference/LICENSES/Multiboard-Licence-2025-12-19.txt",
    "Creative Commons — Attribution": "reference/LICENSES/CC-BY-4.0.txt",
    "Creative Commons — Attribution  — Noncommercial  —  Share Alike":
        "reference/LICENSES/CC-BY-NC-SA-4.0.txt",
}
# Filename suffix -> media type. Only brep/mesh are ever loaded; citation (PDF
# drawings) and archive (original zips) records are measurement-inert.
MEDIA_TYPES = {
    ".step": "brep", ".stp": "brep", ".brep": "brep",
    ".3mf": "mesh", ".stl": "mesh",
    ".pdf": "citation",
    ".zip": "archive",
}
MEASURABLE = frozenset({"brep", "mesh"})
PLANES = ("XY", "XZ", "YZ")
AXES = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def media_type_of(filename: str | Path) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in MEDIA_TYPES:
        raise ValueError(f"{Path(filename).name}: unsupported suffix {suffix!r}")
    return MEDIA_TYPES[suffix]


def load_shape(path: str | Path):
    """Return ``(shape, kind)``; kind is 'brep' or 'mesh'.

    Mesh input goes through ``Mesher().read`` (list[Shape] in build123d 0.11.1);
    several objects are combined into one Compound."""
    from build123d import Compound, Mesher, import_brep, import_step

    path = Path(path)
    kind = media_type_of(path)
    if kind not in MEASURABLE:
        raise ValueError(f"{path.name}: {kind} files are not measurable")
    if not path.is_file():
        raise FileNotFoundError(path)
    if kind == "brep":
        shape = import_brep(str(path)) if path.suffix.lower() == ".brep" else import_step(str(path))
        return shape, kind
    saved = locale.setlocale(locale.LC_ALL)
    try:
        shapes = list(Mesher().read(str(path)))
    finally:
        locale.setlocale(locale.LC_ALL, saved)  # lib3mf resets the process locale to C
    if not shapes:
        raise ValueError(f"{path.name}: mesh file contains no objects")
    return (shapes[0] if len(shapes) == 1 else Compound(children=shapes)), kind


def _r(value: float) -> float:
    out = round(float(value), PRECISION)
    return 0.0 if out == 0 else out  # no -0.0 in the JSON


def _vec(v) -> list[float]:
    return [_r(v.X), _r(v.Y), _r(v.Z)]


def _plane(name: str, offset: float = 0.0):
    from build123d import Plane, Vector

    base = getattr(Plane, name)
    axis = {"XY": 2, "XZ": 1, "YZ": 0}[name]
    origin = [0.0, 0.0, 0.0]
    origin[axis] = float(offset)
    return Plane(origin=Vector(*origin), x_dir=base.x_dir, z_dir=base.z_dir)


def collect_measurements(shape, kind: str, axis: str = "Z",
                         min_plane_area: float = MIN_PLANE_AREA) -> dict:
    """Bounding box / volume / solids for both kinds; analytic faces for brep.

    ``axis`` also summarises the cylinders parallel to it (``coaxial_radii``)
    and the planar faces normal to it (``levels``, their coordinate along it).
    The B-rep bbox is OCC's optimal box, which can overshoot a trimmed
    B-spline face (threads); ``levels`` and section edges are exact."""
    from build123d import GeomType, Vector

    if axis not in AXES:
        raise ValueError(f"axis must be one of {sorted(AXES)}")
    bb = shape.bounding_box(optimal=(kind == "brep"))
    out = {
        "kind": kind,
        "bbox": {"min": _vec(bb.min), "max": _vec(bb.max), "size": _vec(bb.size)},
        "volume": _r(shape.volume),
        "solids": len(shape.solids()),
        "axis": axis,
    }
    if kind != "brep":
        out.update(analytic=MESH_UNSUPPORTED, cylinders=None, planes=None,
                   coaxial_radii=None, levels=None)
        return out

    ax = Vector(*AXES[axis])
    faces = shape.faces()
    cylinders = []
    for face in faces.filter_by(GeomType.CYLINDER):
        rot = face.axis_of_rotation
        cylinders.append({"radius": _r(face.radius), "axis": _vec(rot.direction),
                          "centre": _vec(rot.position)})
    planes = []
    for face in faces.filter_by(GeomType.PLANE):
        if face.area < min_plane_area:
            continue
        planes.append({"normal": _vec(face.normal_at()), "area": _r(face.area),
                       "centre": _vec(face.center())})
    cylinders.sort(key=lambda c: (c["radius"], c["centre"], c["axis"]))
    planes.sort(key=lambda p: (p["normal"], p["centre"], p["area"]))
    parallel = lambda d: abs(abs(Vector(*d).dot(ax)) - 1) < 1e-6  # noqa: E731
    idx = "XYZ".index(axis)
    out.update(
        analytic="ok",
        cylinders=cylinders,
        planes=planes,
        coaxial_radii=sorted({c["radius"] for c in cylinders if parallel(c["axis"])}),
        levels=sorted({p["centre"][idx] for p in planes if parallel(p["normal"])}),
    )
    return out


def write_section(shape, plane, dxf: str | Path | None = None,
                  svg: str | Path | None = None):
    """Section ``shape`` by ``plane``; write DXF/SVG in plane-local coords.

    Returns the plane-local section (a Sketch/Compound)."""
    from build123d import ExportDXF, ExportSVG, Mode, Unit, section

    sk = section(shape, section_by=plane, mode=Mode.PRIVATE)
    local = plane.to_local_coords(sk)
    if not local.edges():
        raise ValueError("section is empty: the plane misses the shape")
    if dxf is not None:
        exporter = ExportDXF(unit=Unit.MM)
        exporter.add_shape(local)
        exporter.write(str(dxf))
    if svg is not None:
        exporter = ExportSVG(unit=Unit.MM, scale=1)
        exporter.add_shape(local)
        exporter.write(str(svg))
    return local


def section_summary(local, plane_name: str, offset: float) -> dict:
    """Edge list of a plane-local section: ``(u, v)`` start/end per edge."""
    edges = []
    for e in local.edges():
        a, b = e.position_at(0), e.position_at(1)
        edges.append({"type": e.geom_type.name, "start": [_r(a.X), _r(a.Y)],
                      "end": [_r(b.X), _r(b.Y)]})
    edges.sort(key=lambda e: (e["start"][1], e["start"][0], e["end"], e["type"]))
    bb = local.bounding_box()
    return {"plane": plane_name, "offset": _r(offset), "coords": "plane-local (u, v)",
            "area": _r(sum(f.area for f in local.faces())),
            "bbox": {"min": [_r(bb.min.X), _r(bb.min.Y)], "max": [_r(bb.max.X), _r(bb.max.Y)]},
            "edges": edges}


def format_table(m: dict) -> str:
    rows = [("kind", m["kind"]), ("solids", m["solids"]), ("volume mm^3", m["volume"]),
            ("bbox min", m["bbox"]["min"]), ("bbox max", m["bbox"]["max"]),
            ("bbox size", m["bbox"]["size"])]
    if m.get("analytic") == "ok":
        rows += [("cylinder faces", len(m["cylinders"])),
                 (f"radii || {m['axis']}", m["coaxial_radii"]),
                 ("planar faces", len(m["planes"])),
                 (f"levels along {m['axis']}", m["levels"])]
    else:
        rows.append(("analytic", m.get("analytic")))
    if "section" in m:
        s = m["section"]
        rows += [("section", f"{s['plane']} @ {s['offset']}"), ("section edges", len(s["edges"])),
                 ("section bbox", f"{s['bbox']['min']} .. {s['bbox']['max']}")]
    width = max(len(k) for k, _ in rows)
    return "\n".join(f"{k:<{width}}  {v}" for k, v in rows)


# --- provenance recording ----------------------------------------------------

def sha256_of(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_source(sha256: str, manifest: Path = SOURCE_MANIFEST) -> tuple[dict, dict]:
    """The unique (record, version) whose version sha256 equals ``sha256``."""
    records = json.loads(Path(manifest).read_text(encoding="utf-8"))["sources"]
    hits = [(r, v) for r in records for v in r["versions"] if v["sha256"] == sha256]
    if len(hits) != 1:
        raise LookupError(f"sha256 {sha256[:12]} matches {len(hits)} source versions (need 1)")
    return hits[0]


def rel(path: str | Path, root: Path = ROOT) -> str:
    return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()


def load_artifacts(manifest: Path = ARTIFACT_MANIFEST) -> list[dict]:
    if not Path(manifest).exists():
        return []
    data = json.loads(Path(manifest).read_text(encoding="utf-8"))
    if data.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError(f"artifact manifest: schema must be {ARTIFACT_SCHEMA}")
    return data["artifacts"]


def dump_artifacts(artifacts: list[dict]) -> str:
    ordered = sorted(artifacts, key=lambda a: a["file"])
    return json.dumps({"schema": ARTIFACT_SCHEMA, "artifacts": ordered},
                      indent=2, ensure_ascii=False) + "\n"


def record_artifacts(outputs: list[Path], source: Path, command: str, plane: str | None,
                     *, manifest: Path = ARTIFACT_MANIFEST,
                     sources: Path = SOURCE_MANIFEST, today: str | None = None,
                     root: Path = ROOT) -> list[dict]:
    """Upsert one artifact-manifest entry per output file (keyed by ``file``)."""
    record, version = find_source(sha256_of(source), sources)
    if record["licence"] not in LICENCE_TEXTS:
        raise LookupError(f"no licence text for {record['licence']!r}: add it to LICENCE_TEXTS")
    entries = {a["file"]: a for a in load_artifacts(manifest)}
    new = []
    for out in outputs:
        entry = {
            "file": rel(out, root),
            "sha256": sha256_of(out),
            "source_file_id": record["source_file_id"],
            "source_sha256": version["sha256"],
            "source_group_id": record["source_group_id"],
            "licence": record["licence"],
            "licence_text": LICENCE_TEXTS[record["licence"]],
            "measured_on": today or datetime.date.today().isoformat(),
            "tool_version": TOOL_VERSION,
            "command": command,
            "plane": plane,
        }
        entries[entry["file"]] = entry
        new.append(entry)
    Path(manifest).write_text(dump_artifacts(list(entries.values())), encoding="utf-8")
    return new


# --- CLI ---------------------------------------------------------------------

def measure(path: str | Path, *, axis: str = "Z", plane: str | None = None, offset: float = 0.0,
            dxf=None, svg=None) -> dict:
    """load -> collect -> optional section: the full JSON document for one file."""
    import build123d

    path = Path(path)
    shape, kind = load_shape(path)
    m = {"tool": TOOL_VERSION, "build123d": build123d.__version__,
         "source": {"filename": path.name, "sha256": sha256_of(path), "media_type": kind}}
    m.update(collect_measurements(shape, kind, axis))
    if plane:
        local = write_section(shape, _plane(plane, offset), dxf, svg)
        m["section"] = section_summary(local, plane, offset)
    return m


def _arg_path(path: Path) -> str:
    try:
        return rel(path)
    except ValueError:
        return str(path)


def command_line(args) -> str:
    """The reproducible command (run from build123d/) that produced the outputs."""
    parts = [_arg_path(args.file), "--axis", args.axis]
    if args.plane:
        parts += ["--plane", args.plane, "--z", f"{args.z:g}"]
    for flag in ("json", "dxf", "svg"):
        if getattr(args, flag) is not None:
            parts += [f"--{flag}", _arg_path(getattr(args, flag))]
    return "uv run tools/measure_step.py " + shlex.join(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--axis", choices=sorted(AXES), default="Z")
    ap.add_argument("--plane", choices=PLANES, help="section plane (through --z)")
    ap.add_argument("--z", type=float, default=0.0,
                    help="world coordinate along the plane normal (XY->Z, XZ->Y, YZ->X)")
    ap.add_argument("--json", type=Path, help="write the measurement JSON here")
    ap.add_argument("--dxf", type=Path, help="write the section as DXF (needs --plane)")
    ap.add_argument("--svg", type=Path, help="write the section as SVG (needs --plane)")
    ap.add_argument("--record", action="store_true",
                    help="upsert the outputs into reference/artifact-manifest.json")
    ap.add_argument("--artifact-manifest", type=Path, default=ARTIFACT_MANIFEST, help=argparse.SUPPRESS)
    ap.add_argument("--source-manifest", type=Path, default=SOURCE_MANIFEST, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if (args.dxf or args.svg) and not args.plane:
        ap.error("--dxf/--svg need --plane")
    outputs = [p for p in (args.json, args.dxf, args.svg) if p is not None]
    if args.record and not outputs:
        ap.error("--record needs at least one of --json/--dxf/--svg")

    try:
        kind = media_type_of(args.file)
        if kind not in MEASURABLE:
            print(f"{args.file.name}: {kind} files are not measurable", file=sys.stderr)
            return 2
        m = measure(args.file, axis=args.axis, plane=args.plane, offset=args.z,
                    dxf=args.dxf, svg=args.svg)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        args.json.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    print(format_table(m))

    if args.record:
        command = command_line(args)
        try:
            entries = record_artifacts(outputs, args.file, command, args.plane,
                                       manifest=args.artifact_manifest, sources=args.source_manifest)
        except LookupError as exc:
            print(f"error: cannot record: {exc}", file=sys.stderr)
            return 1
        for e in entries:
            print(f"recorded {e['file']} <- {e['source_file_id']} @ {e['source_sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
