"""Committed reference artefacts and the provenance tags built on them (pst-ff71).

Offline (PR CI): the artefact manifest covers exactly the files in
reference/measured/, every sha256 matches, every artefact's foreign key
``(source_file_id, source_sha256)`` resolves to one source version, the
licence text is committed, no upstream original is committed, and every
[V] value is re-derived from the committed measurement JSON.
Upstream (trusted workflow): the JSON measurements regenerate exactly from
the mirrored originals, independent of the recorded build123d version;
the measurement-tool version must match and SVG bytes remain identical.
"""

import datetime
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import ezdxf
import pytest
from opengrid import constants as oc

ROOT = Path(__file__).resolve().parent.parent  # build123d/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import measure_step as ms  # noqa: E402
from holders import cup_lid  # noqa: E402
from multibuild import constants as c  # noqa: E402
from multibuild import tile  # noqa: E402
from multibuild.multiconnect import POCKET_DEPTH  # noqa: E402
from reference_pull import load_sources, local_path  # noqa: E402

REFERENCE = ROOT / "reference"
MEASURED = REFERENCE / "measured"
UPSTREAM_SUFFIXES = {".step", ".stp", ".brep", ".3mf", ".stl", ".pdf", ".zip"}
ENTRY_KEYS = ("file", "sha256", "source_file_id", "source_sha256", "source_group_id",
              "licence", "licence_text", "measured_on", "tool_version", "command", "plane")


def _artifacts():
    return ms.load_artifacts()


def _versions():
    return {(r["source_file_id"], v["sha256"]): r for r in load_sources() for v in r["versions"]}


def test_artifact_manifest_covers_every_artifact():
    on_disk = {p.relative_to(ROOT).as_posix() for p in MEASURED.rglob("*") if p.is_file()}
    listed = [a["file"] for a in _artifacts()]
    assert len(listed) == len(set(listed)), "duplicate artefact entries"
    assert on_disk and set(listed) == on_disk


def test_artifact_sha256_matches():
    for a in _artifacts():
        assert ms.sha256_of(ROOT / a["file"]) == a["sha256"], a["file"]


def test_source_fk_resolves():
    versions = _versions()
    for a in _artifacts():
        record = versions.get((a["source_file_id"], a["source_sha256"]))
        assert record is not None, f"{a['file']}: FK does not resolve"
        assert a["source_group_id"] == record["source_group_id"]
        assert a["licence"] == record["licence"]


def test_entries_complete():
    for a in _artifacts():
        assert set(a) == set(ENTRY_KEYS), a["file"]
        assert all(a[k] for k in ENTRY_KEYS if k != "plane"), a["file"]
        assert a["licence_text"] == ms.LICENCE_TEXTS[a["licence"]]
        assert (ROOT / a["licence_text"]).is_file()
        datetime.date.fromisoformat(a["measured_on"])
        assert a["tool_version"] == ms.TOOL_VERSION
        argv = shlex.split(a["command"])
        assert argv[:3] == ["uv", "run", "tools/measure_step.py"] and a["file"] in argv
        assert a["plane"] in (*ms.PLANES, None)
        if a["plane"]:
            assert argv[argv.index("--plane") + 1] == a["plane"]


def test_every_source_licence_has_committed_text():
    for licence in {r["licence"] for r in load_sources()}:
        assert (ROOT / ms.LICENCE_TEXTS[licence]).is_file(), licence


def _tracked_reference_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "."], cwd=REFERENCE,
                             capture_output=True, check=True)
        return [REFERENCE / p for p in out.stdout.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):  # no git: walk, minus the gitignored mirror
        return [p for p in REFERENCE.rglob("*") if p.is_file() and "upstream" not in p.relative_to(REFERENCE).parts]


def test_no_upstream_originals_committed():
    files = _tracked_reference_files()
    assert files
    bad = [p.relative_to(ROOT).as_posix() for p in files if p.suffix.lower() in UPSTREAM_SUFFIXES]
    assert not bad, f"upstream originals must never be committed (reference/FETCH.md): {bad}"


# --- root asset exception register ------------------------------------------

ASSET_SUFFIXES = {".scad", ".stl", ".step", ".3mf", ".ttf"}


def exception_register_rows(document: str) -> list[str]:
    """Read only scope cells in the exception register, never the licence table."""
    section = document.split("### Exception register\n", 1)[1]
    section = re.split(r"^#{1,6} ", section, maxsplit=1, flags=re.MULTILINE)[0]
    return [line.split("|")[1].strip() for line in section.splitlines()
            if line.startswith("|") and line.split("|")[1].strip().startswith("`assets/")]


def _row_asset_set(row: str) -> str | None:
    match = re.match(r"`?(assets/[^/`]+/)", row)
    return match[1] if match else None


def unregistered_asset_sets(asset_dirs: Mapping[str, list[str]], register_rows: list[str]) -> list[str]:
    registered = {_row_asset_set(row) for row in register_rows}
    return sorted(set(asset_dirs) - registered)


def _expand_braces(path: str) -> list[str]:
    match = re.search(r"\{([^{}]+)\}", path)
    if not match:
        return [path]
    return [expanded for choice in match[1].split(",")
            for expanded in _expand_braces(path[:match.start()] + choice + path[match.end():])]


def _resolve_paths(path: str, asset_dir: str, existing_paths: set[str]) -> set[str]:
    """Resolve set-relative patterns first, then repository-root paths."""
    for pattern in (asset_dir + path, path):
        matches = {p for p in existing_paths if len(Path(p).parts) == len(Path(pattern).parts)
                   and Path(p).match(pattern.rstrip("/"))}
        if matches:
            return matches
    return set()


def _mentions_file(document: str, path: str) -> bool:
    # Boundaries prevent x.stl from matching other-x.stl, subdir/x.stl or x.stl.old.
    return re.search(r"(?<![\w./-])" + re.escape(path) + r"(?=$|[\s`'\":,;)]|\.(?:\s|$))", document) is not None


def uncovered_asset_files(
    asset_dirs: Mapping[str, list[str]], register_rows: list[str],
    existing_paths: set[str], pointer_texts: Mapping[str, str],
) -> list[str]:
    """Pure coverage/existence check; all filesystem evidence is supplied by the caller."""
    problems = []
    for asset_dir, files in asset_dirs.items():
        covered = set()
        for row in register_rows:
            if _row_asset_set(row) != asset_dir:
                continue
            for token in re.findall(r"`([^`]+)`", row):
                # Ignore revisions and suffix-only prose (e.g. 'no .shapr').
                if "/" not in token and Path(token).suffix.lower() not in ASSET_SUFFIXES:
                    continue
                for path in _expand_braces(token):
                    matches = _resolve_paths(path, asset_dir, existing_paths)
                    if not matches:
                        problems.append(f"{asset_dir}: missing registered path {path}")
                    covered.update(matches)

            # A pointer grants only the files actually named by that document.
            for pointer in re.findall(
                r"(?:enumerated|hashes|SHA256) in [`\[]?((?:[\w-]+/)*(?:NOTICE|SHA256SUMS))", row,
            ):
                pointers = _resolve_paths(pointer, asset_dir, set(pointer_texts))
                if not pointers:
                    problems.append(f"{asset_dir}: missing register pointer {pointer}")
                for name in pointers:
                    hashes = set(re.findall(r"^[a-fA-F0-9]{64} [ *](.+)$", pointer_texts[name], re.MULTILINE))
                    for file in files:
                        candidates = {file, file.removeprefix(asset_dir)}
                        # SHA256SUMS commonly lists names relative to its own directory.
                        parent = str(Path(name).parent) + "/"
                        if Path(name).name == "SHA256SUMS" and file.startswith(parent):
                            candidates.add(file.removeprefix(parent))
                        mentioned = (bool(candidates & hashes) if Path(name).name == "SHA256SUMS" else
                                     any(_mentions_file(pointer_texts[name], p) for p in candidates))
                        if mentioned:
                            covered.add(file)
        problems.extend(f"{file}: not covered by exception register"
                        for file in files if Path(file).suffix.lower() in ASSET_SUFFIXES and file not in covered)
    return sorted(problems)


def _root_asset_evidence():
    repo = ROOT.parent
    out = subprocess.run(["git", "ls-files", "-z"], cwd=repo, capture_output=True, check=True)
    tracked = [p for p in out.stdout.decode().split("\0") if p]
    asset_dirs = {str(Path(p).parent) + "/": [] for p in tracked
                  if re.fullmatch(r"assets/[^/]+/NOTICE", p)}
    for directory in asset_dirs:
        asset_dirs[directory] = [p for p in tracked if p.startswith(directory)]
    # Include directories for adaptation paths, but do not mask deleted tracked files.
    existing = {p for p in tracked if (repo / p).exists()}
    existing.update(str(parent) for p in tuple(existing) for parent in Path(p).parents)
    pointers = {p: (repo / p).read_text(encoding="utf-8")
                for files in asset_dirs.values() for p in files
                if Path(p).name in {"NOTICE", "SHA256SUMS"} and (repo / p).is_file()}
    rows = exception_register_rows((ROOT / "docs/provenance.md").read_text(encoding="utf-8"))
    return asset_dirs, rows, existing, pointers


def test_root_asset_sets_are_registered():
    asset_dirs, rows, _, _ = _root_asset_evidence()
    assert asset_dirs, "expected tracked root assets with NOTICE files"
    assert not (missing := unregistered_asset_sets(asset_dirs, rows)), missing


def test_root_asset_files_are_covered():
    assert not (problems := uncovered_asset_files(*_root_asset_evidence())), "\n".join(problems)


def test_root_asset_register_negative_control():
    directory = "assets/example-port/"
    files = [directory + "NOTICE", directory + "mesh/x.stl"]
    asset_dirs = {directory: files}
    row = f"`{directory}`: `mesh/x.stl`"
    assert unregistered_asset_sets(asset_dirs, []) == [directory]
    assert unregistered_asset_sets(asset_dirs, [row]) == []
    assert uncovered_asset_files(asset_dirs, [], set(files), {}) == [
        files[1] + ": not covered by exception register",
    ]
    assert uncovered_asset_files(asset_dirs, [row], set(files) | {directory.rstrip('/')}, {}) == []


@pytest.mark.parametrize("suffix", sorted(ASSET_SUFFIXES))
def test_root_asset_directory_row_is_not_blanket_coverage(suffix):
    directory = "assets/example-port/"
    file = directory + "mesh/new" + suffix
    problems = uncovered_asset_files({directory: [file]}, [f"`{directory}`"],
                                     {directory.rstrip('/'), file}, {})
    assert problems == [file + ": not covered by exception register"]


@pytest.mark.parametrize("pointer", ["NOTICE", "mesh/SHA256SUMS"])
def test_root_asset_pointer_covers_only_named_files(pointer):
    directory = "assets/example-port/"
    files = [directory + "mesh/x.stl", directory + "mesh/other x.stl"]
    row = f"`{directory}`: hashes in `{pointer}`"
    existing = set(files) | {directory.rstrip('/'), directory + pointer}
    args = ({directory: files}, [row], existing)
    prefix = "0" * 64 + "  " if pointer.endswith("SHA256SUMS") else ""
    listing = prefix + "mesh/x.stl\n" + prefix + "mesh/other x.stl"
    assert uncovered_asset_files(*args, {directory + pointer: listing}) == []
    problems = uncovered_asset_files(*args, {directory + pointer: listing.replace("mesh/x.stl", "mesh/x.stl.old")})
    assert problems == [files[0] + ": not covered by exception register"]
    assert uncovered_asset_files(*args, {})  # a pointer must resolve


def test_root_asset_enumerations_and_adaptations_must_exist():
    directory = "assets/example-port/"
    files = [directory + "mesh/x.stl", directory + "step/with spaces.step"]
    row = f"`{directory}`: `mesh/{{x,y}}.stl`, `step/*.step`. Adaptation: `build123d/example/`"
    existing = set(files) | {directory.rstrip('/')}
    problems = uncovered_asset_files({directory: files}, [row], existing, {})
    assert problems == [f"{directory}: missing registered path build123d/example/",
                        f"{directory}: missing registered path mesh/y.stl"]
    existing.update({directory + "mesh/y.stl", "build123d/example"})
    assert uncovered_asset_files({directory: files}, [row], existing, {}) == []


def test_exception_register_parser_uses_only_scope_cells():
    row = "`assets/example-port/`: `mesh/x.stl`"
    doc = ("| `assets/outside/` | MIT |\n### Exception register\n"
           "| Exact file set / scope | Licence |\n| --- | --- |\n"
           f"| {row} | MIT | `assets/not-a-scope/` |\n"
           "## Next section\n| `assets/also-outside/` | MIT |\n")
    assert exception_register_rows(doc) == [row]


# --- values re-derived from the committed measurement JSON -------------------

def _json(name):
    return json.loads((MEASURED / f"{name}.json").read_text(encoding="utf-8"))


def _verticals(m):
    """{|u|: [(v0, v1), ...]} for the section's straight edges at constant u > 0."""
    out = {}
    for e in m["section"]["edges"]:
        (u0, v0), (u1, v1) = e["start"], e["end"]
        if e["type"] == "LINE" and abs(u0 - u1) < 1e-4 and u0 > 0 and abs(v1 - v0) > 1e-3:
            out.setdefault(round(u0, 4), []).append(tuple(sorted((v0, v1))))
    return {u: sorted(spans) for u, spans in out.items()}


def _pitch(spans):
    starts = [a for a, _ in spans]
    steps = [b - a for a, b in zip(starts, starts[1:])]
    assert steps and max(steps) - min(steps) < 1e-3, steps  # B-spline sections wobble ~5e-4
    return sum(steps) / len(steps)


def _chamfer(m, u_face):
    """The straight edge leaving the face (v=0) at u=u_face: (Δu per Δv, end)."""
    [e] = [e for e in m["section"]["edges"] if e["type"] == "LINE"
           and e["start"] == [u_face, 0.0] and e["end"][1] > 0]
    (u0, v0), (u1, v1) = e["start"], e["end"]
    return (u0 - u1) / (v1 - v0), (u1, v1)


def _derived():
    cell, multi, small = _json("mb-large-octagon-hole-positive"), _json("mb-multihole-negative"), _json("mb-small-thread-negative")
    thickness = max(cell["levels"]) - min(cell["levels"])
    mv = _verticals(multi)
    outer, inner = max(mv), min(mv)
    large_pitch = _pitch(mv[outer])
    mouth_u = multi["bbox"]["size"][0] / 2
    run, _ = _chamfer(multi, mouth_u)
    large_taper = (mouth_u - inner) / run
    sv = _verticals(small)
    s_mouth_u = small["bbox"]["size"][0] / 2
    s_run, (s_throat_u, s_taper) = _chamfer(small, s_mouth_u)
    assert s_run == pytest.approx(1)  # 45°
    male = _verticals(_json("mb-small-vertical-12-5mm-positive"))
    return {
        "PITCH": cell["section"]["bbox"]["max"][0] - cell["section"]["bbox"]["min"][0],
        "TILE_THICKNESS": thickness,
        "SMALL_HOLE_MOUTH_D": 2 * s_mouth_u,
        "SMALL_HOLE_THROAT_D": 2 * s_throat_u,
        "SMALL_HOLE_TAPER_DEPTH": s_taper,
        "mouth_across_flats": 2 * mouth_u,
        "central_across_flats": 2 * inner,
        "band_height": thickness - 2 * large_taper,
        "helix_outer_d": 2 * outer,
        "helix_inner_d": 2 * inner,
        "helix_outer_width": mv[outer][0][1] - mv[outer][0][0],
        "helix_inner_width": large_pitch - (mv[inner][0][1] - mv[inner][0][0]),
        "helix_pitch": large_pitch,
        "LARGE_HOLE_TAPER_DEPTH": large_taper,
        "small_thread_major_d": 2 * max(sv),
        "small_thread_pitch": _pitch(sv[max(sv)]),
        "small_thread_outer_width": sv[max(sv)][0][1] - sv[max(sv)][0][0],
        "small_male_pitch": _pitch(male[max(male)]),
    }


def _all_tags():
    return {**c.PROVENANCE, **c.LARGE_HOLE_PROFILE}


def test_constants_are_measured_values():
    """pst-ozpae adopted every measured value: no [C] tag remains."""
    derived = _derived()
    for key, p in _all_tags().items():
        assert p.status == "V", key
        assert (ROOT / p.locator).is_file(), key
        assert derived[key] == pytest.approx(p.value, abs=2e-3), key
    # Doc-only small-thread values (no constant; research §2, library.md).
    assert derived["small_thread_pitch"] == pytest.approx(3.125, abs=1e-3)
    assert derived["small_male_pitch"] == pytest.approx(3.125, abs=1e-3)
    assert derived["small_thread_outer_width"] == pytest.approx(0.625, abs=1e-3)
    assert derived["small_thread_major_d"] == pytest.approx(7.0, abs=1e-3)


# pst-ozpae invariant 3: the MultiBuild consumers read multibuild.constants.
TILE_SOURCES = {
    "thickness": c.PROVENANCE["TILE_THICKNESS"],
    "large_mouth_across_flats": c.LARGE_HOLE_PROFILE["mouth_across_flats"],
    "large_central_across_flats": c.LARGE_HOLE_PROFILE["central_across_flats"],
    "large_taper_depth": c.PROVENANCE["LARGE_HOLE_TAPER_DEPTH"],
    "small_mouth_d": c.PROVENANCE["SMALL_HOLE_MOUTH_D"],
    "small_throat_d": c.PROVENANCE["SMALL_HOLE_THROAT_D"],
    "small_taper_depth": c.PROVENANCE["SMALL_HOLE_TAPER_DEPTH"],
}
CONSUMERS = ("multibuild/tile.py", "holders/cup_lid.py", "tests/test_multibuild.py", "tests/test_cup_lid.py")
# Replaced cited values: thickness, mouth, band, taper, helix outer Ø / inner
# width. 2.4 (old band) is omitted: it collides with the cup-lid backing rule.
SUPERSEDED = re.compile(r"(?<![\d.])(6\.4|7\.5|2\.9|1\.75|22\.6|1\.583)(?!\d)")


def test_tile_profile_is_the_constants():
    assert tile.TILE_PROFILE.keys() == TILE_SOURCES.keys()
    for key, p in TILE_SOURCES.items():
        assert tile.TILE_PROFILE[key] is p, key


def test_consumers_hold_no_superseded_copies():
    assert cup_lid.MOUTH is c.SMALL_HOLE_MOUTH_D and cup_lid.PITCH is c.PITCH
    for rel in CONSUMERS:
        for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if "MULTICONNECT_ROUND_HEAD_" in line:  # opengrid library head radius 7.5
                continue
            assert not SUPERSEDED.search(line), f"{rel}:{n}: {line.strip()}"


def test_grid_phase_from_artifacts():
    cell = _json("mb-large-octagon-hole-positive")["section"]["bbox"]
    small = _json("mb-small-thread-hole-positive")["section"]["bbox"]
    centre = lambda bb: [(a + b) / 2 for a, b in zip(bb["min"], bb["max"])]  # noqa: E731
    offset = [s - l for s, l in zip(centre(small), centre(cell))]
    large0, small0 = c.large_hole_center(0, 0), c.small_hole_center(0, 0)
    assert offset == pytest.approx([small0[0] - large0[0], small0[1] - large0[1]])


def test_multiconnect_profile_matches_pinned_library():
    """Official v2 modelling files == the pinned opengrid head/cutter (research §3)."""
    head = _json("mc-v2-round")
    hv = _verticals(head)
    assert head["coaxial_radii"] == [oc.MULTICONNECT_ROUND_HEAD_TOP_RADIUS, oc.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS]
    assert hv[oc.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS] == [(0.0, oc.MULTICONNECT_ROUND_HEAD_BOTTOM_HEIGHT)]
    top = oc.MULTICONNECT_ROUND_HEAD_TOP_RADIUS
    height = head["bbox"]["size"][2]
    assert hv[top] == [(height - oc.MULTICONNECT_ROUND_HEAD_TOP_HEIGHT, height)]
    assert height == pytest.approx(oc.MULTICONNECT_ROUND_HEAD_BOTTOM_HEIGHT + oc.MULTICONNECT_ROUND_HEAD_TAPER_HEIGHT
                                   + oc.MULTICONNECT_ROUND_HEAD_TOP_HEIGHT)
    for name in ("mc-v2-round-negative", "mc-v2-slot-negative"):
        neg = _json(name)
        assert neg["bbox"]["size"][2] == pytest.approx(POCKET_DEPTH, abs=1e-4)
        assert neg["bbox"]["size"][0] == pytest.approx(2 * (oc.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS + 0.15))
        nv = _verticals(neg)
        assert sorted(nv) == pytest.approx([top + 0.15, oc.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS + 0.15])
    # The official slot segment is one 25 mm board pitch long.
    assert _json("mc-v2-slot-negative")["bbox"]["size"][1] == pytest.approx(c.PITCH)


# --- upstream: artefacts regenerate from the mirrored originals --------------

def _json_artifacts():
    return [a for a in _artifacts() if a["file"].endswith(".json")]


@pytest.mark.upstream
@pytest.mark.parametrize("artifact", _json_artifacts(), ids=lambda a: a["file"])
def test_artifacts_regenerate(artifact, tmp_path):
    record = _versions()[(artifact["source_file_id"], artifact["source_sha256"])]
    path = local_path(record, artifact["source_sha256"])
    if not path.is_file():
        pytest.skip(f"{artifact['source_file_id']} not pulled (reference/FETCH.md)")
    argv = shlex.split(artifact["command"])
    plane = argv[argv.index("--plane") + 1] if "--plane" in argv else None
    offset = float(argv[argv.index("--z") + 1]) if "--z" in argv else 0.0
    axis = argv[argv.index("--axis") + 1] if "--axis" in argv else "Z"
    stem = ROOT / artifact["file"][:-len(".json")]
    dxf, svg = tmp_path / "s.dxf", tmp_path / "s.svg"
    m = ms.measure(path, axis=axis, plane=plane, offset=offset,
                   dxf=dxf if plane else None, svg=svg if plane else None)
    committed = json.loads((ROOT / artifact["file"]).read_text(encoding="utf-8"))
    # The library stamp records provenance, not geometry. Keep every measured
    # field exact and require the same measurement-tool schema separately.
    assert m["tool"] == committed["tool"] == ms.TOOL_VERSION
    provenance = {"tool", "build123d"}
    measured = {k: v for k, v in json.loads(json.dumps(m)).items() if k not in provenance}
    expected = {k: v for k, v in committed.items() if k not in provenance}
    assert measured == expected
    if plane:
        assert svg.read_bytes() == stem.with_suffix(".svg").read_bytes()
        # DXF bytes embed save timestamps; compare the drawing content.
        kinds = lambda p: sorted(e.dxftype() for e in ezdxf.readfile(p).modelspace())  # noqa: E731
        assert kinds(dxf) == kinds(stem.with_suffix(".dxf"))
