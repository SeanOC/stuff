"""MultiBuild Fix Point slot + head (pst-7shtl): re-derived from measurements.

Offline tests read only the committed measurement JSON. The ``upstream``
tests compare the rebuilt solids with the mirrored originals
(reference/FETCH.md); PR CI deselects them.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from build123d import Align, Box, Pos, import_step  # noqa: E402
from multibuild import fixpoint as fp  # noqa: E402
from reference_pull import load_sources, local_path  # noqa: E402

MEASURED = ROOT / "reference" / "measured"
_CENTER = (Align.CENTER, Align.CENTER, Align.CENTER)


def _json(name):
    return json.loads((MEASURED / f"{name}.json").read_text(encoding="utf-8"))


def _lines(m):
    """Section LINE edges as sorted ((u0, v0), (u1, v1)) tuples, rounded."""
    out = set()
    for e in m["section"]["edges"]:
        assert e["type"] == "LINE"
        out.add(tuple(sorted((tuple(round(c, 3) for c in e["start"]),
                              tuple(round(c, 3) for c in e["end"])))))
    return out


def _vol(shape):
    return sum(s.volume for s in shape.solids()) if shape is not None else 0.0


def _width(shape, *, y, z, axis="X"):
    """Extent along X of ``shape`` in a thin slab at (y, z)."""
    inter = shape.intersect(Pos(0, y, z) * Box(100, 0.02, 0.02, align=_CENTER))
    solids = list(inter.solids()) if inter is not None else []
    if not solids:
        return 0.0
    xs = [v.X for s in solids for v in s.vertices()]
    return round(max(xs) - min(xs), 4)


# --- offline: constants == committed measurements ---------------------------

def test_constants_are_measured():
    for key, p in fp.PROVENANCE.items():
        assert p.status == "V", key
        assert (ROOT / p.locator).is_file(), key
        assert getattr(fp, key) == p.value, key


def test_remix_is_licensed():
    head = Path(fp.__file__).read_text(encoding="utf-8").splitlines()[:3]
    assert "Multiboard Licence" in head[0] and "NOT covered by" in head[1]
    notice = (Path(fp.__file__).parent / "LICENSE-MULTIBOARD.md").read_text(encoding="utf-8")
    assert "multibuild/fixpoint.py" in notice


def test_slot_section_is_the_measured_profile():
    m = _json("mb-fix-point-slot-negative")
    # YZ section at X=0: u = slot Y (slide axis), v = Z (depth).
    lip, deep, land = fp.MOUTH_INRADIUS, fp.DEEP_INRADIUS, fp.LIP_LAND
    ours = {
        ((fp.WELL_END, 0.0), (lip, 0.0)),
        ((lip, 0.0), (lip, land)),
        ((lip, land), (deep, fp.LIP_TOP)),
        ((deep, fp.LIP_TOP), (deep, fp.SLOT_DEPTH)),
        ((fp.TAIL_END, fp.SLOT_DEPTH), (deep, fp.SLOT_DEPTH)),
        ((fp.TAIL_END, fp.TAIL_UNDERCUT_Z + fp.WELL_END - fp.TAIL_END), (fp.TAIL_END, fp.SLOT_DEPTH)),
        ((fp.TAIL_END, fp.TAIL_UNDERCUT_Z + fp.WELL_END - fp.TAIL_END), (fp.WELL_END, fp.TAIL_UNDERCUT_Z)),
        ((fp.WELL_END, 0.0), (fp.WELL_END, fp.TAIL_UNDERCUT_Z)),
    }
    assert _lines(m) == {tuple(sorted(tuple(round(c, 3) for c in p) for p in e)) for e in ours}
    assert m["bbox"]["size"][0] == pytest.approx(2 * fp.DEEP_INRADIUS)
    assert m["bbox"]["size"][1] == pytest.approx(fp.SLOT_LENGTH)
    assert m["solids"] == 1


def test_head_section_is_the_measured_profile():
    m = _json("mb-fix-point-positive")
    assert m["coaxial_radii"] == [fp.NECK_RADIUS, fp.HEAD_RADIUS]
    assert m["bbox"]["size"] == pytest.approx([2 * fp.HEAD_FLAT, 2 * fp.HEAD_RADIUS, fp.HEAD_HEIGHT])
    assert fp.NOTCH_FLOOR in m["levels"]
    # XZ section at Y=0: neck, 45-degree flare to the flats, flats to the top.
    r, flat_z = fp.NECK_RADIUS, fp.NECK_HEIGHT + fp.HEAD_FLAT - fp.NECK_RADIUS
    assert ((r, 0.0), (r, fp.NECK_HEIGHT)) in _lines(m)
    assert ((r, fp.NECK_HEIGHT), (fp.HEAD_FLAT, round(flat_z, 3))) in _lines(m)
    assert ((fp.HEAD_FLAT, round(flat_z, 3)), (fp.HEAD_FLAT, fp.HEAD_HEIGHT)) in _lines(m)


@pytest.mark.parametrize(("build", "name"), [(fp.slot_body, "mb-fix-point-slot-negative"),
                                             (fp.head_body, "mb-fix-point-positive")])
def test_rebuilt_volume_and_bbox_match_measurement(build, name):
    m, part = _json(name), build()
    assert part.is_valid and len(part.solids()) == 1
    assert part.volume == pytest.approx(m["volume"], rel=5e-3)
    bb = part.bounding_box()
    # The slot file's only feature below Z=0 is a 0.5 mm locator tip at the
    # origin (0.02 mm^3, outside any consumer); it is not rebuilt.
    assert [bb.min.X, bb.min.Y] == pytest.approx(m["bbox"]["min"][:2], abs=0.05)
    assert [bb.max.X, bb.max.Y, bb.max.Z] == pytest.approx(m["bbox"]["max"], abs=0.05)
    assert bb.min.Z == pytest.approx(0, abs=1e-6)


# --- offline: the head fits the slot and is captured -------------------------

@pytest.fixture(scope="module")
def plate():
    """A 40 x 50 x 8 block with one slot; material Z=0..8 (slot frame)."""
    return Pos(0, -3, 0) * Box(40, 50, 8, align=(Align.CENTER, Align.CENTER, Align.MIN)) - fp.slot_body()


def test_head_seats_clear(plate):
    assert _vol(plate & fp.head_body()) < 1e-3


@pytest.mark.parametrize("dist", (0.5, 1.0, 2.0))
def test_head_is_captured_under_the_lip(plate, dist):
    # Pulled straight off the board the flare fouls the lip.
    assert _vol(plate & (Pos(0, 0, -dist) * fp.head_body())) > 5.0


def test_seat_end_is_closed(plate):
    assert _vol(plate & (Pos(0, 1.0, 0) * fp.head_body())) > 10.0


def test_entry_and_slide_are_unobstructed(plate):
    head = fp.head_body()
    for i in range(17):  # straight in at the well, from 4 mm off the board
        assert _vol(plate & (Pos(0, -fp.TRAVEL, -i * 0.25) * head)) < 1e-3
    for i in range(25):  # then the slide to the seat
        assert _vol(plate & (Pos(0, -fp.TRAVEL + i * 0.25, 0) * head)) < 1e-3


def test_consumer_frame():
    bb = fp.slot_cutter().bounding_box()
    assert (bb.min.X, bb.max.X) == pytest.approx((-fp.DEEP_INRADIUS, fp.DEEP_INRADIUS), abs=1e-6)
    assert (bb.min.Y, bb.max.Y) == pytest.approx((0, fp.POCKET_DEPTH), abs=1e-6)
    # Lip end up, well below.
    assert (bb.min.Z, bb.max.Z) == pytest.approx((fp.TAIL_END, fp.DEEP_INRADIUS), abs=1e-6)
    seated = fp.seat_location(0, 0) * fp.head()
    hb = seated.bounding_box()
    assert (hb.min.Y, hb.max.Y) == pytest.approx((0, fp.HEAD_HEIGHT), abs=1e-6)
    assert (hb.min.Z + hb.max.Z) / 2 == pytest.approx(0, abs=1e-6)
    entry = fp.entry_location(0, 0) * fp.head()
    assert entry.bounding_box().min.Z == pytest.approx(hb.min.Z - fp.TRAVEL, abs=1e-6)


# --- upstream: equality with the mirrored originals ---------------------------

def _original(source_file_id):
    [record] = [r for r in load_sources() if r["source_file_id"] == source_file_id]
    path = local_path(record, record["current"])
    if not path.is_file():
        pytest.skip(f"{source_file_id} not pulled (reference/FETCH.md)")
    return import_step(path)


# Slot stations: the -Y taper at full depth, the lip band at the +Y end,
# the well and the seat at the face. Head: neck, flare, flats.
SLOT_STATIONS = [(-9, 3.0), (-11, 3.0), (-13, 3.0), (-14.7, 3.0), (-14.7, 1.0), (7.0, 1.0),
                 (7.0, 2.0), (8.3, 2.8), (0.0, 0.2), (-6.0, 0.2), (3.0, 1.5)]
HEAD_STATIONS = [(0.0, 0.2), (0.0, 1.0), (0.0, 2.0), (6.0, 2.8), (3.0, 2.8), (-7.5, 2.8)]


@pytest.mark.upstream
@pytest.mark.parametrize(("build", "source", "stations"), [
    (fp.slot_body, "multibuild-fix-point-slots/fix-point-slot-negative.step", SLOT_STATIONS),
    (fp.head_body, "multibuild-fix-points/fix-point-positive.step", HEAD_STATIONS)],
    ids=["slot", "head"])
def test_rebuild_equals_original(build, source, stations):
    ref, ours = _original(source), build()
    assert ours.volume == pytest.approx(ref.volume, rel=5e-3)
    rb, ob = ref.bounding_box(), ours.bounding_box()
    assert [ob.min.X, ob.min.Y, ob.max.X, ob.max.Y, ob.max.Z] == pytest.approx(
        [rb.min.X, rb.min.Y, rb.max.X, rb.max.Y, rb.max.Z], abs=0.05)
    assert rb.min.Z >= -0.1 - 1e-6  # the slot's locator tip, see above
    # Nearly identical solids: the symmetric difference is the locator tip.
    assert _vol(ours - ref) < 0.05 and _vol(ref - ours) < 0.05
    for y, z in stations:
        assert _width(ours, y=y, z=z) == pytest.approx(_width(ref, y=y, z=z), abs=0.05), (y, z)
