"""Export registered models: STL (print), GLB (viewer), PNG (review).

Default mode:
    uv run python scripts/export.py
Builds EVERY registered model (smoke included) at its defaults and writes
out/<name>.{stl,glb,png}; PNGs contain iso/front/top/section/underside.
Pass --commit-review to also update tracked non-smoke review PNGs and
analytic section SVG goldens in docs/renders/{review,sections}/.

Presets-only mode (build-time baking, bead pst-pa1o):
    uv run python scripts/export.py --presets-only TARGET_DIR
For every APP-LISTED (non-smoke) registered model, builds each of its
presets and writes exactly three artifacts per preset into TARGET_DIR:

    TARGET_DIR/<model-slug>/<preset-id>.stl   # print download
    TARGET_DIR/<model-slug>/<preset-id>.glb   # viewer geometry
    TARGET_DIR/<model-slug>/<preset-id>.png   # gallery thumbnail

plus, ONLY for a model tagged "multi-colour" (labels L2):

    TARGET_DIR/<model-slug>/<preset-id>.3mf        # one object, part i on filament i+1
    TARGET_DIR/<model-slug>/<preset-id>-base.stl   # filament 1 body
    TARGET_DIR/<model-slug>/<preset-id>-text.stl   # filament 2 body

Single source of truth (bead pst-1vi5): the thumbnail is rendered from
the same built part as the GLB/STL, so a model or preset change can
never leave the gallery card showing stale geometry. The gallery's
/api/thumbnail route serves this baked PNG for build123d models (the
first preset), exactly as /api/bd-asset serves the baked GLB/STL.

Contract (validated by tests/test_presets_bake.py):
  - every registered app-listed model appears (no silent skips),
  - every preset of every such model appears,
  - names are deterministic and filesystem-safe (slug + preset id, both
    URL-safe by registry validation),
  - exactly STL + GLB + PNG per preset (thumbnail is a bake output, not
    a separate committed review artifact), plus 3MF + -base/-text STLs for
    multi-colour models only.
"""
import argparse
import copy
import io
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import trimesh

from build123d import Color, Compound, export_stl as _native_export_stl, export_gltf  # noqa: E402

from holders.registry import (all_models, resolve_colour_parts, resolve_mount_fixtures,  # noqa: E402
                              resolve_preview_parts)
from scripts.thumbnail import PlaneSpec, ReviewContext, render_review, render_thumbnail  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "out"


def export_stl(part, path):
    """Export native geometry, dropping only triangles with repeated vertices.

    OCP emits a collapsed seam triangle at a true cone apex (tip diameter
    zero). It encloses no volume but makes edge-count manifold checks fail.
    Remove those triangles after STL vertex welding; do not fill holes,
    smooth geometry, or remove legitimate small features.
    """
    if not _native_export_stl(part, str(path)):
        raise ValueError(f'STL export failed: {path}')
    mesh = trimesh.load_mesh(path)
    f = mesh.faces
    keep = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 2] != f[:, 0])
    if not keep.all():
        mesh.update_faces(keep)
        mesh.export(str(path), file_type='stl')
    return True


def export_glb(part, path, colour_parts=None) -> None:
    """The viewer GLB: ``part`` as one uncoloured mesh, or one node per colour part.

    colour_parts: resolve_preview_parts(spec, values) — [(name, part, rgba)]
    or None. None writes exactly export_gltf(part) (every single-colour model
    and the raised label stay byte-identical); otherwise each part is a named
    child carrying its own rgba, so the GLB has one material per filament
    (pst-5b83s). No display transform: the exporter's own -90°X Z-up -> Y-up
    root rotation is the only one, so the viewer's compass basis holds.
    Shared by the bake and services/bd-render.
    """
    if colour_parts is None:
        export_gltf(part, str(path), binary=True)
        return
    nodes = []
    for name, shape, rgba in colour_parts:
        node = copy.copy(shape)  # label/colour the copy, not the caller's part
        node.label, node.color = name, Color(*rgba)
        nodes.append(node)
    export_gltf(Compound(children=nodes), str(path), binary=True)
    _matte_glb_materials(Path(path))


def _matte_glb_materials(path: Path) -> None:
    """Set metallicFactor 0 on every material of a binary glTF, in place.

    OCCT writes only baseColorFactor, and glTF's default metallicFactor is
    1: a metal with no environment map renders the white inlay a dull grey
    barely lighter than the near-black base. Filament is a dielectric.
    """
    import json
    import struct
    data = path.read_bytes()
    (json_len,) = struct.unpack_from('<I', data, 12)
    doc = json.loads(data[20:20 + json_len])
    for material in doc.get('materials', []):
        material.setdefault('pbrMetallicRoughness', {})['metallicFactor'] = 0.0
    chunk = json.dumps(doc, separators=(',', ':')).encode()
    chunk += b' ' * (-len(chunk) % 4)  # GLB chunks are 4-byte aligned, JSON padded with spaces
    rest = data[20 + json_len:]
    path.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(chunk) + len(rest))
                     + struct.pack('<I4s', len(chunk), b'JSON') + chunk + rest)


def export_3mf_one_object(named, path, object_name: str) -> None:
    """ONE 3MF build item: a components object whose parts are the named meshes.

    named: [(name, part, rgba)], part i on filament i + 1 (labels D10; moved
    here from holders/label_demo.py in L2 so the bake and bd-render share it).

    build123d's Mesher adds one build item per solid (a text Compound becomes
    one slicer object per glyph), so this writes the core-spec structure with
    lib3mf directly. Bambu Studio ignores mesh names and base-material
    colours; the Metadata/model_settings.config sidecar names the parts and
    puts part i on filament i + 1. Never declare Application=BambuStudio:
    Bambu Studio then expects a full project and crashes on this file.
    Without a project_settings.config Bambu Studio shows "not from Bambu Lab,
    load geometry data and color data only" but keeps each part's extruder
    (labels D10-revised); writing one would load our print config over the
    user's presets, which is worse than the notice.

    Byte-stable for the same input: lib3mf's random production-extension
    UUIDs are replaced by uuid5 of object_name + part name.
    """
    import locale
    import uuid
    import zipfile
    from build123d import Mesher

    def stable_uuid(*key: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, '/'.join(('stuff-3mf', object_name, *key))))

    mesher = Mesher()  # owns the lib3mf wrapper + model; its _mesh helpers weld vertices
    wrapper, model = mesher.wrapper, mesher.model
    group = model.AddBaseMaterialGroup()
    assembly = model.AddComponentsObject()
    assembly.SetName(object_name)
    assembly.SetUUID(stable_uuid('object'))
    part_ids = []
    for name, shape, rgba in named:
        verts, tris = Mesher._mesh_shape(copy.deepcopy(shape), 0.005, 0.1)
        mesh = model.AddMeshObject()
        mesh.SetName(name)
        mesh.SetUUID(stable_uuid('part', name))
        mesh.SetGeometry(*Mesher._create_3mf_mesh(verts, tris))
        mat = group.AddMaterial(name, wrapper.FloatRGBAToColor(*rgba))
        mesh.SetObjectLevelProperty(group.GetResourceID(), mat)
        if not mesh.IsManifoldAndOriented():
            raise RuntimeError(f'3MF part {name} is not manifold and oriented')
        component = assembly.AddComponent(mesh, wrapper.GetIdentityTransform())
        component.SetUUID(stable_uuid('component', name))
        part_ids.append((mesh.GetResourceID(), name))
    model.AddBuildItem(assembly, wrapper.GetIdentityTransform()).SetUUID(stable_uuid('item'))
    model.SetBuildUUID(stable_uuid('build'))
    saved = locale.setlocale(locale.LC_ALL)
    try:
        mesher.write(str(path))
    finally:
        locale.setlocale(locale.LC_ALL, saved)  # lib3mf resets the process locale to C
    settings = [f'<object id="{assembly.GetResourceID()}">',
                f'  <metadata key="name" value="{object_name}"/>',
                '  <metadata key="extruder" value="1"/>']
    for filament, (part_id, name) in enumerate(part_ids, start=1):
        settings += [f'  <part id="{part_id}" subtype="normal_part">',
                     f'    <metadata key="name" value="{name}"/>',
                     f'    <metadata key="extruder" value="{filament}"/>',
                     '  </part>']
    xml = '\n'.join(['<?xml version="1.0" encoding="UTF-8"?>', '<config>',
                     *('  ' + line for line in settings + ['</object>']),
                     '</config>', ''])
    # Fixed timestamp: writestr(name) stamps the wall clock, and the bake must
    # be byte-stable for the same text.
    entry = zipfile.ZipInfo('Metadata/model_settings.config', date_time=(1980, 1, 1, 0, 0, 0))
    with zipfile.ZipFile(path, 'a', zipfile.ZIP_DEFLATED) as package:
        package.writestr(entry, xml, compress_type=zipfile.ZIP_DEFLATED)


def review_context(spec, values, part) -> ReviewContext:
    """Resolve model-frame planes before passing context to the GLB renderer."""
    sections = spec.review_sections
    if not sections:
        # The first declared mount present under these values (pst-pwtnq).
        fixtures = next((fx for fx in (resolve_mount_fixtures(spec, m, values)
                                       for m in spec.mounts) if fx is not None), None)
        if fixtures is not None:
            normal = tuple(np.cross(fixtures.face_normal, fixtures.entry_axis))
            origin = tuple(fixtures.seat_locs[0].position)
            plane = PlaneSpec(origin, normal, "mount plane through first seat")
        else:
            plane = PlaneSpec(tuple(part.bounding_box().center()), (1, 0, 0),
                              "bounding-box centre")
        sections = (plane,)
    return ReviewContext(spec.slug, spec.print_orientation, sections, spec.mounts)


def section_svg(part, plane: PlaneSpec) -> str:
    """Analytic section in plane-local mm, with 3-decimal SVG coordinates."""
    from build123d import ExportSVG, Plane, section
    frame = Plane(origin=plane.origin, z_dir=plane.normal)
    outline = section(part, section_by=frame)
    if not outline.edges():
        raise ValueError(f"empty section: {plane.label}")
    exporter = ExportSVG(precision=3, margin=1)
    exporter.add_shape(frame.to_local_coords(outline))
    buf = io.BytesIO()
    exporter.write(buf)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring(buf.getvalue())
    numeric_attrs = {"d", "points", "viewBox", "transform", "width", "height",
                     "x", "y", "cx", "cy", "rx", "ry", "r", "stroke-width"}
    number = r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?"
    def rounded(match):
        value = round(float(match.group()), 3)
        # Integer SVG arc flags must remain 0/1, not 0.000/1.000.
        return str(int(value)) if value.is_integer() else f"{value:.3f}"
    for element in root.iter():
        for key, value in list(element.attrib.items()):
            if key in numeric_attrs:
                element.set(key, re.sub(number, rounded, value))
    # OCCT may enumerate disconnected wires in a different order per process.
    # Outline-only groups have no painting-order dependence.
    for element in root.iter():
        element[:] = sorted(element, key=lambda child: (child.tag, sorted(child.attrib.items())))
    ET.indent(root)
    return ET.tostring(root, encoding="unicode") + "\n"


def export_all(*, commit_review: bool = False) -> int:
    """Export every model at defaults, optionally refreshing review artifacts."""
    OUT.mkdir(exist_ok=True)
    specs = all_models()
    if not specs:
        print("no models registered"); return 1
    for spec in specs:
        values = spec.resolve_values()
        part = spec.build(values)
        stl = OUT / f"{spec.name}.stl"
        glb = OUT / f"{spec.name}.glb"
        png = OUT / f"{spec.name}.png"
        export_stl(part, str(stl))
        export_glb(part, glb, resolve_preview_parts(spec, values))
        ctx = review_context(spec, values, part)
        started = time.perf_counter()
        render_review(glb, png, ctx=ctx)
        elapsed = time.perf_counter() - started
        if commit_review and not spec.is_smoke:
            renders = OUT.parent / "docs" / "renders"
            (renders / "review").mkdir(parents=True, exist_ok=True)
            (renders / "sections").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(png, renders / "review" / f"{spec.slug}.png")
            (renders / "sections" / f"{spec.slug}.svg").write_text(
                section_svg(part, ctx.sections[0]), encoding="utf-8")
        print(f"review {spec.slug}: {elapsed:.3f}s; volume={part.volume:.6f} mm3")
        print(f"{spec.name}: vol={part.volume:.0f}mm3 -> {stl.name}, {glb.name}, {png.name}")
    return 0


def export_presets_only(target: Path) -> int:
    """Bake every preset of every app-listed model into target/<slug>/<preset-id>.{stl,glb,png}."""
    target.mkdir(parents=True, exist_ok=True)
    specs = [s for s in all_models() if not s.is_smoke]
    if not specs:
        print("no app-listed models registered"); return 1
    baked = 0
    for spec in specs:
        if not spec.presets:
            # Registry validation forbids app-listed models without presets,
            # but fail loudly here too: a silent skip would leak into CI.
            print(f"SKIP {spec.name}: no presets registered", file=sys.stderr)
            return 1
        for preset in spec.presets:
            values = spec.resolve_values(preset.values)
            part = spec.build(values)
            if part.volume <= 0:
                print(f"SKIP {spec.name}/{preset.id}: zero volume", file=sys.stderr)
                return 1
            model_dir = target / spec.slug
            model_dir.mkdir(exist_ok=True)
            stl = model_dir / f"{preset.id}.stl"
            glb = model_dir / f"{preset.id}.glb"
            png = model_dir / f"{preset.id}.png"
            export_stl(part, str(stl))
            export_glb(part, glb, resolve_preview_parts(spec, values))
            # Thumbnail rendered from the SAME GLB the detail viewer loads,
            # using its smooth vertex normals through a depth-buffered
            # software rasteriser (pst-o0wy) — matches the live preview and
            # keeps the pst-1vi5 single-source-of-truth property.
            render_thumbnail(glb, png)
            if spec.is_multi_colour:
                # Gated: every other model's bake output stays exactly STL+GLB+PNG.
                named = resolve_colour_parts(spec, preset.values)
                export_3mf_one_object(named, model_dir / f"{preset.id}.3mf",
                                      f"{spec.slug}-{preset.id}")
                for (_, shape, _), role in zip(named, ("base", "text")):
                    export_stl(shape, str(model_dir / f"{preset.id}-{role}.stl"))
            baked += 1
            print(f"{spec.name}/{preset.id}: vol={part.volume:.0f}mm3 -> {stl}, {glb}, {png}")
    print(f"baked {baked} presets from {len(specs)} models into {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--presets-only",
        metavar="TARGET_DIR",
        help="bake every preset of every app-listed model into TARGET_DIR and exit",
    )
    parser.add_argument("--commit-review", action="store_true",
                        help="write non-smoke review PNGs and section SVGs to docs/renders")
    args = parser.parse_args()
    if args.presets_only and args.commit_review:
        parser.error("--commit-review cannot be combined with --presets-only")
    if args.presets_only:
        return export_presets_only(Path(args.presets_only))
    return export_all(commit_review=args.commit_review)


if __name__ == "__main__":
    raise SystemExit(main())
