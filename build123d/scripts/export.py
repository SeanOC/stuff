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
    TARGET_DIR/<model-slug>/<preset-id>-<part-name>.stl   # one per colour part,
                                                          # named by colour_parts

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
                              resolve_preview_parts, in_print_frame)
from profiles import PROFILES  # noqa: E402
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
    puts part i on filament i + 1. Never declare Application=BambuStudio
    here: Bambu Studio then expects a full project and crashes on this file.
    Without a project_settings.config Bambu Studio shows "not from Bambu Lab,
    load geometry data and color data only" but keeps each part's extruder
    (labels D10-revised). A full project for one printer is the opt-in
    apply_printer_profile below (D10 revised, pst-jyey1).

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


# Bambu Studio project markers (bbs_3mf.cpp in bambulab/BambuStudio; checked
# against a 02.08.02.61 project saved from the GUI, pst-jyey1 rev 1).
BAMBU_NS = 'http://schemas.bambulab.com/package/2021'
# Depth kept free behind the part for the prime tower: the 8-filament sign's
# tower measured 66 x 66.2 mm with its brim on the H2C (pst-jyey1 A2).
PRIME_TOWER_RESERVE = 70.0
PLATE_MARGIN = 2.0


def _bbox(polygon) -> tuple[float, float, float, float]:
    """['0x0', '330x0', ...] (Bambu's point strings) -> x0, x1, y0, y1."""
    xs, ys = zip(*(map(float, point.split('x')) for point in polygon))
    return min(xs), max(xs), min(ys), max(ys)


def _place_on_plate(model: str, settings: dict) -> tuple[str, float, float]:
    """Build-item transform that puts the part on the plate, plus the prime
    tower's corner, deterministic for the same mesh.

    The generic 3MF has no item transform (the print frame is centred on the
    origin), so a project would open with the part off the plate. Put the part
    at the plate's front, centred on the area every extruder reaches, and the
    prime tower behind it; turn the part 90 degrees about Z when only that
    leaves room for the tower (the 240 x 300 sign on the 330 x 320 H2C bed,
    which is what Bambu Studio's own arrange does). Never touches the mesh.
    """
    import numpy as np

    vertices = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', model), float)
    lo, hi = vertices.min(0), vertices.max(0)
    px0, px1, py0, py1 = _bbox(settings['printable_area'])
    # Area all extruders reach (the H2C's two differ by 5 mm on each side).
    reach = [_bbox(area.split(',')) for area in settings.get('extruder_printable_area') or []]
    rx0, rx1 = (max(b[0] for b in reach), min(b[1] for b in reach)) if reach else (px0, px1)
    tower_w = float(settings['prime_tower_width'])
    for turned in (False, True):
        # Turning +90 degrees about Z maps (x, y) to (-y, x).
        (x0, x1), (y0, y1) = (((-hi[1], -lo[1]), (lo[0], hi[0])) if turned
                              else ((lo[0], hi[0]), (lo[1], hi[1])))
        if (x1 - x0 <= px1 - px0 - 2 * PLATE_MARGIN
                and y1 - y0 + PLATE_MARGIN + PRIME_TOWER_RESERVE <= py1 - py0 - 2 * PLATE_MARGIN):
            break
    else:
        raise ValueError(f'part {hi[0] - lo[0]:.1f} x {hi[1] - lo[1]:.1f} mm does not fit the '
                         f'plate with a prime tower behind it')
    half = (x1 - x0) / 2
    centre = min(max((rx0 + rx1) / 2, px0 + PLATE_MARGIN + half), px1 - PLATE_MARGIN - half)
    tx, ty, tz = centre - (x0 + x1) / 2, py0 + PLATE_MARGIN - y0, -lo[2]
    # Bambu Studio fills the 3x3 column-outer (bbs_3mf.cpp
    # bbs_get_transform_from_3mf_specs_string; add_transformation writes the
    # same order), so '0 1 0 -1 0 0 0 0 1' reads as (x, y) -> (-y, x). A
    # row-major reader (PrusaSlicer/Orca) would turn the other way.
    rotation = '0 1 0 -1 0 0 0 0 1' if turned else '1 0 0 0 1 0 0 0 1'
    transform = f'{rotation} {tx:.4f} {ty:.4f} {tz:.4f}'
    return transform, (rx0 + rx1 - tower_w) / 2, y1 + ty + PLATE_MARGIN


def apply_printer_profile(src_3mf: Path, dst_3mf: Path, profile, named) -> None:
    """Copy the generic 3MF at src_3mf into a slicer project for profile.

    A pure transform of the generic bytes (no rebuild) shared by the bake and
    bd-render. Every member is copied unchanged except 3D/3dmodel.model, which
    gains the Bambu Studio namespace, requiredextensions="p", the Application
    and BambuStudio:3mfVersion metadata and a build-item transform that places
    the part on the plate (_place_on_plate); one member is added:
    Metadata/project_settings.config, the profile's template with
    filament_colour[i] = part i's colour and the prime tower moved behind the
    part. Metadata/model_settings.config stays the only part -> filament map
    (part i on filament i + 1). [Content_Types].xml needs no entry: configs
    are found by name. Only Application and 3mfVersion are copied from a GUI
    project's metadata: its DesignerUserId is the saver's account id.
    """
    import json
    import zipfile

    if len(named) > profile.filament_slots:
        raise ValueError(f'{len(named)} parts but printer profile {profile.id} '
                         f'has {profile.filament_slots} filament slots')
    settings = profile.settings()
    with zipfile.ZipFile(src_3mf) as generic:
        members = [(info, generic.read(info)) for info in generic.infolist()]
    model_index = next(i for i, (info, _) in enumerate(members) if info.filename == '3D/3dmodel.model')
    model = members[model_index][1].decode('utf-8')
    transform, tower_x, tower_y = _place_on_plate(model, settings)

    root = re.search(r'<model [^>]*>', model)
    if root is None or 'requiredextensions' in root.group(0) or model.count('<item ') != 1:
        raise ValueError(f'{src_3mf} is not a generic export_3mf_one_object file')
    # String splice, not ElementTree: re-serialising renames the p: prefix
    # that requiredextensions="p" refers to.
    model = (model[:root.start()]
             + root.group(0)[:-1] + f' xmlns:BambuStudio="{BAMBU_NS}" requiredextensions="p">\n'
             + f'\t<metadata name="Application">{profile.application}</metadata>\n'
             + '\t<metadata name="BambuStudio:3mfVersion">1</metadata>'
             + model[root.end():]).replace('<item ', f'<item transform="{transform}" ', 1)
    members[model_index] = (members[model_index][0], model.encode('utf-8'))

    colours = list(settings['filament_colour'])
    for slot, (_, _, rgba) in enumerate(named):
        colours[slot] = '#' + ''.join(f'{round(c * 255):02X}' for c in rgba[:3])
    settings['filament_colour'] = colours
    settings['wipe_tower_x'] = [f'{tower_x:.2f}']
    settings['wipe_tower_y'] = [f'{tower_y:.2f}']
    config = zipfile.ZipInfo('Metadata/project_settings.config', date_time=(1980, 1, 1, 0, 0, 0))
    config.compress_type = zipfile.ZIP_DEFLATED
    members.append((config, (json.dumps(settings, indent=4) + '\n').encode('utf-8')))
    with zipfile.ZipFile(dst_3mf, 'w', zipfile.ZIP_DEFLATED) as package:
        for info, data in members:
            package.writestr(info, data)


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
    if spec.print_frame is not None:
        from build123d import Pos
        frame = spec.print_frame(values)
        origin = frame.position
        sections = tuple(PlaneSpec(tuple((frame * Pos(*p.origin)).position),
                                   tuple((frame * Pos(*p.normal)).position - origin), p.label)
                         for p in sections)
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
        ctx = review_context(spec, values, part)
        part = in_print_frame(spec, values, part)
        stl = OUT / f"{spec.name}.stl"
        glb = OUT / f"{spec.name}.glb"
        png = OUT / f"{spec.name}.png"
        export_stl(part, str(stl))
        export_glb(part, glb, resolve_preview_parts(spec, values))
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
    """Bake every preset of every app-listed model into target/<slug>/<preset-id>.{stl,glb,png}.

    Multi-colour models add <preset-id>.3mf (generic), <preset-id>.<profile-id>.3mf
    per printer profile and one STL per part.
    """
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
            part = in_print_frame(spec, values, spec.build(values))
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
                generic = model_dir / f"{preset.id}.3mf"
                export_3mf_one_object(named, generic, f"{spec.slug}-{preset.id}")
                for profile in PROFILES.values():
                    apply_printer_profile(generic, model_dir / f"{preset.id}.{profile.id}.3mf",
                                          profile, named)
                for name, shape, _ in named:
                    export_stl(shape, str(model_dir / f"{preset.id}-{name}.stl"))
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
