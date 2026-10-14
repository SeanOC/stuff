"""pst-sx1g3: the print-audit cache never hides a regression (I2-I5).

Key-level tests compare ``audit_cache.key`` directly (no audit); the round
trip, switch and budget tests audit a tiny box against a per-test store. The
two fresh-process HIT rows and the every-preset determinism gate run in
subprocesses (``python -m tests.test_audit_cache <row>``).
"""
import importlib.util
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from build123d import (Axis, Box, Face, Location, Pos, RegularPolygon, Solid,
                       Vector, fillet)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import holders.printer as printer  # noqa: E402
from tests import audit_cache  # noqa: E402
from tests import print_audit as pa  # noqa: E402

UP = (0.0, 0.0, 1.0)


@pytest.fixture
def store(tmp_path, monkeypatch):
    """A private, empty cache directory for this test."""
    monkeypatch.setenv("BD_AUDIT_CACHE", str(tmp_path))
    return tmp_path


def _counts():
    return dict(audit_cache.COUNTS)


def _delta(before):
    return {k: audit_cache.COUNTS[k] - before[k] for k in ("hits", "misses", "off")}


def _filleted_box(x=20.0):
    """A box with filleted bottom edges: the report carries DownwardFillet
    entries, so the round trip exercises the nested dataclass."""
    box = Box(x, 20, 10)
    return fillet(box.edges().group_by(Axis.Z)[0], 2)


def _hex_facet():
    """drawer/shell.py:487-488's ceiling waiver shape: a 0.001 mm extrusion of
    a hexagonal face (circumradius 3, a vertex on +X)."""
    return Solid.extrude(Face(RegularPolygon(3, 6).wire()), Vector(0, 0, .001))


def _rect_facet():
    """A rectangle with the hex facet's exact bbox."""
    bb = _hex_facet().bounding_box()
    return Pos(0, 0, .0005)*Box(bb.size.X, bb.size.Y, .001)


def _rounded_bbox(shape):
    bb = shape.bounding_box()
    return tuple(round(v, 6) + 0.0 for v in (*bb.min, *bb.max))


# --- I3 hit semantics -----------------------------------------------------

def test_hit_returns_an_equal_report(store):
    part = _filleted_box()
    before = _counts()
    cold = pa.audit(part, UP, model="box")
    warm = pa.audit(part, UP, model="box")
    assert _delta(before) == {"hits": 1, "misses": 1, "off": 0}
    assert cold.downward_fillets, "fixture must exercise DownwardFillet"
    assert warm.format() == cold.format()
    for name in pa.PrintAuditReport.__dataclass_fields__:
        assert getattr(warm, name) == getattr(cold, name), name
        assert type(getattr(warm, name)) is type(getattr(cold, name)), name
    for fillet_ in warm.downward_fillets:
        assert isinstance(fillet_, pa.DownwardFillet)
        assert isinstance(fillet_.location, tuple)
    assert len(list(store.glob("*.json"))) == 1


def test_an_audit_that_raises_stores_nothing(store, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("audit failed")

    monkeypatch.setattr(pa, "_audit", boom)
    with pytest.raises(RuntimeError):
        pa.audit(_filleted_box(), UP)
    assert not list(store.glob("*.json"))


# --- I4 never hides a regression ------------------------------------------

def test_same_part_rebuilt_is_a_hit_and_a_changed_dimension_a_miss(store):
    pa.audit(_filleted_box(), UP)
    before = _counts()
    pa.audit(_filleted_box(), UP)
    assert _delta(before)["hits"] == 1
    before = _counts()
    pa.audit(_filleted_box(20.01), UP)
    assert _delta(before) == {"hits": 0, "misses": 1, "off": 0}


def test_changed_audit_source_is_a_miss(monkeypatch):
    part = _filleted_box()
    k = audit_cache.key(part, UP)
    monkeypatch.setattr(audit_cache, "_source_hash", lambda: "edited")
    assert audit_cache.key(part, UP) != k


def test_changed_exclusion_list_is_a_miss():
    part = _filleted_box()
    assert (audit_cache.key(part, UP)
            != audit_cache.key(part, UP, exclusions=[(0, 0, 0, 1, 1, 1)])
            != audit_cache.key(part, UP, exclusions=[(0, 0, 0, 1, 1, 2)]))


def test_exclusion_changed_in_shape_not_bbox_is_a_miss():
    """The case a bbox-keyed cache ships green on: same bbox, different BREP,
    different is_inside."""
    hexagon, rect = _hex_facet(), _rect_facet()
    assert _rounded_bbox(hexagon) == _rounded_bbox(rect) == (
        -3.0, -2.598076, 0.0, 3.0, 2.598076, 0.001)
    corner = (2.9, 2.5, .0005)  # inside the rectangle, outside the hexagon
    assert rect.is_inside(corner) and not hexagon.is_inside(corner)
    part = _filleted_box()
    assert (audit_cache.key(part, UP, exclusions=[hexagon])
            != audit_cache.key(part, UP, exclusions=[rect]))


def test_bounded_predicate_with_changed_solid_is_a_miss(monkeypatch):
    """tests/test_gridfinity_capture_bin.py:233's analytic exclusion: same
    class, same bounds, different wrapped solid (gridfinity/bin.py
    underside_exclusions with a changed corner radius)."""
    from gridfinity import bin as gf
    from tests.test_gridfinity_capture_bin import bounded_exclusions

    original = bounded_exclusions(gf.underside_exclusions(2, 2))
    monkeypatch.setattr(gf, "TOP_RADIUS", gf.TOP_RADIUS - .5)
    mutated = bounded_exclusions(gf.underside_exclusions(2, 2))
    (a,), (b,) = original, mutated
    assert type(a) is type(b)
    assert _rounded_bbox(a.solid) == _rounded_bbox(b.solid)
    part = _filleted_box()
    assert (audit_cache.key(part, UP, exclusions=original)
            != audit_cache.key(part, UP, exclusions=mutated))
    # ... and a same-shape predicate built afresh keys identically.
    monkeypatch.setattr(gf, "TOP_RADIUS", gf.TOP_RADIUS + .5)
    again = bounded_exclusions(gf.underside_exclusions(2, 2))
    assert (audit_cache.key(part, UP, exclusions=again)
            == audit_cache.key(part, UP, exclusions=original))


_DOME_SOURCE = '''\
import math


class _DomeSurface:
    def __init__(self, x, y, radius, depth, height):
        self.x, self.y, self.radius, self.depth, self.height = x, y, radius, depth, height

    def is_inside(self, point, tolerance=1e-6):
        x, y, z = point
        return (self.height-self.depth-tolerance <= z <= self.height + tolerance
                and abs(math.hypot(x-self.x, y-self.y)-self.radius)
                <= BAND+tolerance)
'''


def _dome_from_source(tmp_path, monkeypatch, band):
    """holders/cartridge_holder.py's _DomeSurface, loaded from a module whose
    only difference is the radial band literal: same module name, same class
    name, same vars() — only getsource differs."""
    path = tmp_path / "audit_cache_dome_fixture.py"
    path.write_text(_DOME_SOURCE.replace("BAND", band))
    spec = importlib.util.spec_from_file_location("audit_cache_dome_fixture", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)  # inspect resolves via it
    spec.loader.exec_module(module)
    return module._DomeSurface(0, 0, 10, 5, 20)


def test_analytic_predicate_with_changed_source_is_a_miss(tmp_path, monkeypatch):
    part = _filleted_box()
    narrow = _dome_from_source(tmp_path, monkeypatch, ".001")
    k_narrow = audit_cache.key(part, UP, exclusions=[narrow])
    assert k_narrow == audit_cache.key(
        part, UP, exclusions=[_dome_from_source(tmp_path, monkeypatch, ".001")])
    wide = _dome_from_source(tmp_path, monkeypatch, ".05")
    assert type(wide).__qualname__ == type(narrow).__qualname__
    assert type(wide).__module__ == type(narrow).__module__
    assert vars(wide) == vars(narrow)
    assert audit_cache.key(part, UP, exclusions=[wide]) != k_narrow


def test_analytic_predicate_with_changed_state_is_a_miss():
    from holders.cartridge_holder import _DomeSurface

    part = _filleted_box()
    assert (audit_cache.key(part, UP, exclusions=[_DomeSurface(0, 0, 10, 5, 20)])
            != audit_cache.key(part, UP, exclusions=[_DomeSurface(.01, 0, 10, 5, 20)]))


def test_changed_bed_changes_the_key(monkeypatch):
    """I4 bed, KEY half: print_audit freezes the bed at import, so only the
    key (read at call time) can see the edit."""
    part = _filleted_box()
    k = audit_cache.key(part, UP)
    monkeypatch.setattr(printer, "BED_X", 250.0)
    assert audit_cache.key(part, UP) != k


def test_changed_bed_fails_an_oversize_part():
    """I4 bed, BED half: a 300 mm footprint does not fit a 250 mm bed."""
    assert pa.bed_failure((300.0, 10.0, 10.0), bed=(250.0, 320.0, 325.0)) is not None
    assert pa.bed_failure((300.0, 10.0, 10.0)) is None


def test_changed_threshold_constant_changes_the_key(monkeypatch):
    part = _filleted_box()
    k = audit_cache.key(part, UP)
    monkeypatch.setattr(pa, "MIN_WALL_MM", 1.6)
    assert audit_cache.key(part, UP) != k


# --- canonicalisation ------------------------------------------------------

def test_argument_order_does_not_change_the_key():
    part = _filleted_box()
    cutters = [Pos(-5, 0, 0)*Box(1, 1, 1), Pos(5, 0, 0)*Box(1, 2, 1)]
    exclusions = [(0, 0, 0, 1, 1, 1), _hex_facet(), (2, 2, 2, 3, 3, 3)]
    assert (audit_cache.key(part, UP, cutters=cutters, exclusions=exclusions)
            == audit_cache.key(part, UP, cutters=cutters[::-1],
                               exclusions=exclusions[::-1]))


def test_cutters_key_on_the_box_the_audit_sees():
    """A cutter reaches _cutter_boxes AFTER print_frame moves it, and a
    rotated bbox is not the bbox of the rotated cutter: two cutters sharing a
    bbox must key apart once a 45° print_frame turns them."""
    part = _filleted_box()
    bar = Pos(0, 0, 0)*Box(10, 1, 1).rotate(Axis.Z, 45)
    square = Box(*bar.bounding_box().size)
    frame = Location((0, 0, 0), (0, 0, 45))
    assert _rounded_bbox(bar) == _rounded_bbox(square)
    assert (audit_cache.key(part, UP, cutters=[bar])
            == audit_cache.key(part, UP, cutters=[square]))
    assert (audit_cache.key(part, UP, cutters=[bar], print_frame=frame)
            != audit_cache.key(part, UP, cutters=[square], print_frame=frame))


def test_uncanonical_predicate_is_uncacheable(store):
    class Opaque:
        def __init__(self):
            self.handle = object()

        def is_inside(self, point, tolerance=1e-6):
            return False

    with pytest.raises(audit_cache.Uncacheable):
        audit_cache.key(_filleted_box(), UP, exclusions=[Opaque()])
    namespace = {}
    exec("class NoSource:\n"
         "    def is_inside(self, point, tolerance=1e-6):\n"
         "        return False\n", namespace)
    with pytest.raises(audit_cache.Uncacheable):
        audit_cache.key(_filleted_box(), UP, exclusions=[namespace["NoSource"]()])
    before = _counts()
    pa.audit(_filleted_box(), UP, exclusions=[Opaque()])
    assert _delta(before) == {"hits": 0, "misses": 0, "off": 1}
    assert not list(store.glob("*.json"))


# --- I5 location + switch --------------------------------------------------

@pytest.mark.parametrize("value", ["off", "OFF"])
def test_off_switch_disables_the_cache(tmp_path, monkeypatch, value):
    monkeypatch.setenv("BD_AUDIT_CACHE", value)
    monkeypatch.chdir(tmp_path)
    assert audit_cache.cache_dir() is None
    before = _counts()
    pa.audit(_filleted_box(), UP)
    pa.audit(_filleted_box(), UP)
    assert _delta(before) == {"hits": 0, "misses": 0, "off": 2}


def test_default_dir_is_the_gitignored_build123d_cache(monkeypatch):
    monkeypatch.delenv("BD_AUDIT_CACHE", raising=False)
    assert audit_cache.cache_dir() == ROOT / ".cache" / "audit"
    ignored = subprocess.run(["git", "check-ignore", "-q", str(ROOT / ".cache" / "audit" / "x.json")],
                             cwd=ROOT, check=False)
    assert ignored.returncode == 0, "build123d/.cache/ must be gitignored"


def test_disabled_context_forces_a_cold_audit(store):
    pa.audit(_filleted_box(), UP)
    before = _counts()
    with audit_cache.disabled():
        pa.audit(_filleted_box(), UP)
    assert _delta(before) == {"hits": 0, "misses": 0, "off": 1}


@pytest.mark.parametrize("garbage", ["", "{not json", '{"key": "x", "report": {}}',
                                     '{"report": {"model": "box"}}'])
def test_corrupt_entry_is_a_logged_miss(store, caplog, garbage):
    part = _filleted_box()
    path = store / f"{audit_cache.key(part, UP)}.json"
    path.write_text(garbage)
    before = _counts()
    with caplog.at_level(logging.WARNING, logger=audit_cache.__name__):
        report = pa.audit(part, UP)
    assert _delta(before) == {"hits": 0, "misses": 1, "off": 0}
    assert "corrupt" in caplog.text
    assert audit_cache.load(path) == report  # rewritten


def test_summary_line_format():
    line = audit_cache.summary({"hits": 3, "misses": 1, "off": 2, "audit_s": 12.345})
    assert line == "AUDIT-CACHE hits=3 misses=1 off=2 audit_s=12.3"


# --- budget path stays cold ------------------------------------------------

def test_budget_helper_never_times_a_hit(store, monkeypatch):
    """test_print_audit's budget test times a COLD audit even when the store
    is warm and BD_AUDIT_CACHE is on: a memoised hit is re-timed cold."""
    from tests import test_print_audit as tpa

    spec = SimpleNamespace(name="audit-cache-budget-fixture")
    monkeypatch.setattr(tpa, "_build_and_audit",
                        lambda s: pa.audit(_filleted_box(), UP, model=s.name))
    monkeypatch.setattr(tpa, "_AUDITS", {})
    pa.audit(_filleted_box(), UP, model=spec.name)  # warm the store
    report, _, hit = tpa._timed_audit(spec)
    assert hit, "precondition: the warm store answered"
    before = _counts()
    cold_report, elapsed, cold_hit = tpa._timed_audit(spec, cold=True)
    assert not cold_hit and elapsed > 0
    assert _delta(before) == {"hits": 0, "misses": 0, "off": 1}
    assert cold_report == report


# --- fresh-process HIT rows + I2 determinism -------------------------------

def _row_args(row):
    """(part, audit kwargs) of one production audit call."""
    if row == "drawer":  # tests/test_openconnect_drawer.py:316-317, 1x1x1
        from drawer import shell
        from holders import openconnect_drawer as m
        from tests.openconnect_drawer_inventory import wall_regions

        values = dict(horizontal_grids=1, vertical_grids=1, depth_grids=1)
        return m.build(values), dict(
            cutters=shell.slot_fixtures(values).cutters,
            print_frame=m.print_frame(values),
            exclusions=shell.published_ceiling_regions(values)+wall_regions(values))
    if row == "cartridge":  # tests/test_cartridge_holder.py:63-65, defaults
        from holders import cartridge_holder as m

        values = m.SPEC.resolve_values()
        fx = m.mount_fixtures(m.MOUNT, values)
        return m.build(values), dict(
            orientation=m.SPEC.print_orientation,
            cutters=fx.cutters if fx else [],
            exclusions=m.audit_exclusions(values))
    raise ValueError(row)


def _preset_keys():
    """{slug/preset: [part BREP sha, full audit key]} for every manifest preset,
    built with the registry audit's own arguments (cutters, exclusions incl.
    BREP solids and analytic predicates, print_frame)."""
    from holders.registry import all_models
    from tests.test_print_audit import _audit_args

    manifest = json.loads((ROOT / "manifest.json").read_text())
    wanted = {m["slug"]: [p["id"] for p in m["presets"]] for m in manifest["models"]}
    specs = {s.slug: s for s in all_models()}
    out = {}
    for slug, presets in sorted(wanted.items()):
        spec = specs[slug]
        by_id = {p.id: p for p in spec.presets}
        for preset in presets:
            part, kwargs = _audit_args(spec, by_id[preset].values)
            out[f"{slug}/{preset}"] = [audit_cache.brep_sha(part),
                                       audit_cache.key(part, **kwargs)]
    return out


def _start_module(*args, env=None):
    return subprocess.Popen([sys.executable, "-m", "tests.test_audit_cache", *args],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env={**os.environ, **(env or {})})


def _result(proc):
    out, err = proc.communicate()
    assert proc.returncode == 0, err[-4000:]
    return json.loads(out.strip().splitlines()[-1])


def _run_module(*args, env=None):
    return _result(_start_module(*args, env=env))


@pytest.mark.audit
@pytest.mark.parametrize("row", ["drawer", "cartridge"])
def test_production_row_hits_in_a_fresh_process(tmp_path, row):
    """The print_frame + exclusions drawer row and the analytic _DomeSurface
    cartridge row (never one call with both: print_audit's
    ``print_frame * e`` has no _DomeSurface operand) each hit when re-audited
    in a new interpreter, with an identical report."""
    env = {"BD_AUDIT_CACHE": str(tmp_path)}
    cold = _run_module("row", row, env=env)
    warm = _run_module("row", row, env=env)
    assert cold["counts"] == {"hits": 0, "misses": 1, "off": 0}, cold
    assert warm["counts"] == {"hits": 1, "misses": 0, "off": 0}, warm
    assert warm["report"] == cold["report"]
    assert warm["format"] == cold["format"]


@pytest.mark.audit
@pytest.mark.parametrize("row", ["drawer", "cartridge"])
def test_production_row_keys_identically_in_one_process(row):
    """I2, in-process half: the row rebuilt from scratch (part, exclusion
    solids, analytic predicates) yields the same key."""
    first, second = _row_args(row), _row_args(row)
    assert audit_cache.key(first[0], **first[1]) == audit_cache.key(second[0], **second[1])


@pytest.mark.audit  # ~3 min: two interpreters build all 51 presets (I2's 60 s rule)
def test_every_manifest_preset_keys_identically_across_processes():
    """I2: BREP bytes (part + exclusion solids) and the analytic forms are
    stable — every manifest preset yields one key in two interpreters."""
    procs = [_start_module("presets"), _start_module("presets")]
    first, second = (_result(p) for p in procs)
    assert sorted(first) == sorted(second)
    unstable = sorted(k for k in first if first[k] != second[k])
    assert not unstable, unstable


def _main(argv):
    import dataclasses

    if argv[0] == "row":
        part, kwargs = _row_args(argv[1])
        report = pa.audit(part, **kwargs)
        counts = {k: audit_cache.COUNTS[k] for k in ("hits", "misses", "off")}
        print(json.dumps({"counts": counts, "format": report.format(),
                          "report": dataclasses.asdict(report)}))
    elif argv[0] == "presets":
        print(json.dumps(_preset_keys()))
    else:
        raise SystemExit(f"unknown command {argv}")


if __name__ == "__main__":
    _main(sys.argv[1:])
