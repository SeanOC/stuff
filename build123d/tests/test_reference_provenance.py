"""Committed reference artefacts and the provenance tags built on them (pst-ff71).

Offline (PR CI): the artefact manifest covers exactly the files in
reference/measured/, every sha256 matches, every artefact's foreign key
``(source_file_id, source_sha256)`` resolves to one source version, the
licence text is committed, no upstream original is committed, and every
[V] value is re-derived from the committed measurement JSON.
Upstream (trusted workflow): the JSON/SVG artefacts regenerate byte-for-byte
from the mirrored originals.
"""

import datetime
import json
import shlex
import subprocess
import sys
from pathlib import Path

import ezdxf
import pytest
from opengrid import constants as oc

ROOT = Path(__file__).resolve().parent.parent  # build123d/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import measure_step as ms  # noqa: E402
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
        "SMALL_HOLE_THROAT_BAND": thickness - 2 * s_taper,
        "SMALL_HOLE_TAPER_DEPTH": s_taper,
        "mouth_across_flats": 2 * mouth_u,
        "central_across_flats": 2 * inner,
        "band_height": thickness - 2 * large_taper,
        "helix_outer_d": 2 * outer,
        "helix_inner_d": 2 * inner,
        "helix_outer_width": mv[outer][0][1] - mv[outer][0][0],
        "helix_inner_width": large_pitch - (mv[inner][0][1] - mv[inner][0][0]),
        "helix_pitch": large_pitch,
        "large_taper_depth": large_taper,
        "small_thread_major_d": 2 * max(sv),
        "small_thread_pitch": _pitch(sv[max(sv)]),
        "small_thread_outer_width": sv[max(sv)][0][1] - sv[max(sv)][0][0],
        "small_male_pitch": _pitch(male[max(male)]),
    }


# Cited [C] values the official files contradict: measured value + follow-up bead.
DISAGREEMENTS = {
    "TILE_THICKNESS": (6.2, "pst-rs70f"),
    "SMALL_HOLE_MOUTH_D": (8.0, "pst-az4hh"),
    "SMALL_HOLE_THROAT_BAND": (4.2, "pst-hav1h"),
    "band_height": (2.2, "pst-kooqt"),
    "helix_outer_d": (22.5, "pst-23uzq"),
    "helix_inner_width": (1.6, "pst-x5vo8"),
}


def _all_tags():
    return {**c.PROVENANCE, **c.LARGE_HOLE_PROFILE}


def test_confirmed_values_match_artifacts():
    derived = _derived()
    for key, p in _all_tags().items():
        if p.status == "V":
            assert derived[key] == pytest.approx(p.value, abs=2e-3), key
    for key, p in tile.TILE_PROFILE.items():
        name = {"thickness": "TILE_THICKNESS", "large_mouth_across_flats": "mouth_across_flats",
                "large_central_across_flats": "central_across_flats", "small_mouth_d": "SMALL_HOLE_MOUTH_D",
                "small_throat_d": "SMALL_HOLE_THROAT_D", "small_taper_depth": "SMALL_HOLE_TAPER_DEPTH"}.get(key, key)
        assert derived[name] == pytest.approx(p.value, abs=2e-3), key


def test_disagreements_are_recorded_not_applied():
    derived = _derived()
    tags = _all_tags()
    assert {k for k, p in tags.items() if p.status == "C"} == set(DISAGREEMENTS)
    source = (ROOT / "multibuild" / "constants.py").read_text(encoding="utf-8")
    for key, (measured, bead) in DISAGREEMENTS.items():
        assert derived[key] == pytest.approx(measured, abs=2e-3), key
        assert tags[key].value != pytest.approx(measured, abs=2e-3), f"{key} was changed"
        assert f"measured {measured:g}" in source and bead in source, key
    # Doc-only small-thread values (no constant yet): pst-gvdrx, pst-5lum5.
    assert derived["small_thread_pitch"] == pytest.approx(3.125, abs=1e-3)
    assert derived["small_male_pitch"] == pytest.approx(3.125, abs=1e-3)
    assert derived["small_thread_outer_width"] == pytest.approx(0.625, abs=1e-3)
    assert derived["small_thread_major_d"] == pytest.approx(7.0, abs=1e-3)


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
    assert json.loads(json.dumps(m)) == committed
    if plane:
        assert svg.read_bytes() == stem.with_suffix(".svg").read_bytes()
        # DXF bytes embed save timestamps; compare the drawing content.
        kinds = lambda p: sorted(e.dxftype() for e in ezdxf.readfile(p).modelspace())  # noqa: E731
        assert kinds(dxf) == kinds(stem.with_suffix(".dxf"))
