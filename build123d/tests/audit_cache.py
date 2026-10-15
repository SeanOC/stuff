"""Content-addressed cache for ``tests.print_audit.audit`` reports (pst-sx1g3).

An audit of geometry already audited by the same audit code returns the stored
``PrintAuditReport`` instead of re-running the 10-80 s BRep audit. The key is a
sha256 over, in order (docs/print-audit-profile.md "Cache"):

(a) the part's canonical tessellation signature (``shape_sig``: per face,
    the sorted mesh vertices at tolerance 0.01 and the area, rounded to 1e-6;
    faces sorted). The I2 gate found
    BREP bytes unstable: OCCT orders topology records by TShape address, so
    cartridge_holder/default serialises two ways in one process depending on
    what was allocated before it (same geometry, same volume, same mesh);
(b) the audit CODE identity: sha256 of print_audit.py + this file, plus every
    numeric module constant of print_audit read at call time, the bed tuple
    read from ``holders.printer`` at call time and the two frozen bed defaults
    (``bed_failure`` and ``PrintAuditReport.bed_threshold_mm``);
(c) the build123d, OCP and Python versions;
(d) canonical JSON of the other ``audit()`` arguments (``_args``).

Anything the key builder cannot canonicalise faithfully makes the call
uncacheable (it runs, nothing is stored, it counts under ``off``) — never a
guessed key. ``BD_AUDIT_CACHE=<dir>`` moves the store, ``BD_AUDIT_CACHE=off``
disables it; ``disabled()`` forces a cold audit (the budget path).
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import hashlib
import inspect
import io
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_DIR = Path(__file__).resolve().parent.parent / ".cache" / "audit"
# Process counters for the conftest AUDIT-CACHE line. audit_s sums the CPU
# seconds of the cache misses (I6); off/uncacheable audits are counted, not timed.
COUNTS = {"hits": 0, "misses": 0, "off": 0, "audit_s": 0.0}
_forced_off = 0

_CONSTANT = re.compile(r"_?[A-Z][A-Z0-9_]*")
_FLAGS = re.compile(r"[01]{7}")


class Uncacheable(Exception):
    """An audit() argument has no faithful canonical form."""


def cache_dir() -> Path | None:
    """The store directory, or None when caching is off."""
    if _forced_off:
        return None
    env = os.environ.get("BD_AUDIT_CACHE", "")
    if env.strip().lower() == "off":
        return None
    return Path(env) if env else DEFAULT_DIR


@contextlib.contextmanager
def disabled():
    """Force every audit() inside the block to run cold (neither read nor store).

    Anything that times audit() needs it: scripts/profile_print_audit.py and
    scripts/audit_equality_proof.py wrap their calls (pst-dyobq)."""
    global _forced_off
    _forced_off += 1
    try:
        yield
    finally:
        _forced_off -= 1


# --- key ------------------------------------------------------------------

def _num(x) -> float:
    return round(float(x), 6) + 0.0  # + 0.0 folds -0.0 into 0.0


def shape_sig(shape, tolerance=0.01) -> str:
    """sha256 of ``shape``'s canonical tessellation signature (I2): a geometry
    copy meshed at ``tolerance``; per face, its mesh vertices (sorted, rounded
    to 1e-6) and its area (rounded to 1e-6); the faces sorted.

    Triangle centroids (the spec's first fallback) failed the cross-process
    gate on holder-tombstone-sign/pinned: identical vertices (3e-14) but the
    mesher picks different diagonals on planar faces. Per-face vertex sets do
    not depend on the diagonals, and the area separates two faces sharing one
    vertex set (a convex and a notched outline).

    Meshes a copy (``Shape.__deepcopy__`` = BRepBuilderAPI_Copy, no mesh
    carried over), never ``shape`` itself: a triangulation left on the
    audited part would change what a cold audit sees (non-optimal bounding
    boxes read it)."""
    import numpy as np
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location

    mesh = copy.deepcopy(shape)
    mesh.mesh(tolerance)
    faces = []
    for face in mesh.faces():
        loc = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if poly is None:
            raise Uncacheable("a face has no triangulation")
        trsf = loc.Transformation()
        points = (poly.Node(i).Transformed(trsf) for i in range(1, poly.NbNodes() + 1))
        v = np.array([(p.X(), p.Y(), p.Z()) for p in points], dtype=float)
        v = np.round(v, 6) + 0.0  # + 0.0 folds -0.0
        v = np.unique(v, axis=0)  # sorted rows; seam nodes appear twice
        faces.append(hashlib.sha256(v.tobytes()).hexdigest()
                     + f":{_num(face.area)}")
    if not faces:
        raise Uncacheable(f"{type(shape).__qualname__} without faces")
    return hashlib.sha256("\n".join(sorted(faces)).encode()).hexdigest()


def brep_sha(shape) -> str:
    """sha256 of ``shape``'s BREP text without triangulation, with the
    Free/Modified/Checked TShape bits zeroed (state, not geometry)."""
    from OCP.BRepTools import BRepTools
    from OCP.Message import Message_ProgressRange
    from OCP.TopTools import TopTools_FormatVersion

    buf = io.BytesIO()
    BRepTools.Write_s(shape.wrapped, buf, False, False,
                      TopTools_FormatVersion.TopTools_FormatVersion_CURRENT,
                      Message_ProgressRange())
    lines = buf.getvalue().split(b"\n")
    # A TShape record's flags line is the 7-digit bit string immediately
    # before its sub-shape line, which always ends with '*'.
    for i in range(len(lines) - 1):
        line = lines[i].strip()
        if (len(line) == 7 and _FLAGS.fullmatch(line.decode("ascii", "replace"))
                and lines[i + 1].rstrip().endswith(b"*")):
            lines[i] = b"000" + line[3:]
    return hashlib.sha256(b"\n".join(lines)).hexdigest()


def _source_hash() -> str:
    """sha256 of the audit code: print_audit.py + this file."""
    from tests import print_audit

    h = hashlib.sha256()
    for path in (print_audit.__file__, __file__):
        h.update(Path(path).read_bytes())
    return h.hexdigest()


def _thresholds() -> dict:
    """Every value the report can depend on that lives outside the part,
    read now (a monkeypatched or edited constant changes the key)."""
    import holders.printer as printer
    from tests import print_audit as pa

    out = {name: _exact(value) for name, value in vars(pa).items()
           if _CONSTANT.fullmatch(name)}
    out["holders.printer.BED"] = _exact((printer.BED_X, printer.BED_Y, printer.BED_Z))
    out["bed_failure.default"] = _exact(pa.bed_failure.__defaults__)
    out["report.bed_threshold_mm.default"] = _exact(
        pa.PrintAuditReport.__dataclass_fields__["bed_threshold_mm"].default)
    return out


def _exact(value):
    """A threshold value, unrounded (constants carry no float noise)."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)):
        return [_exact(v) for v in value]
    raise Uncacheable(f"audit constant of type {type(value).__qualname__}")


def _versions() -> dict:
    import build123d
    import OCP

    return {"build123d": build123d.__version__,
            "OCP": getattr(OCP, "__version__", "?"),
            "python": sys.version}


def _canon(value):
    """TOTAL canonical JSON form of an analytic predicate's state (I1(d))."""
    from build123d import BoundBox, Shape

    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        return _num(value)
    # BoundBox, Location, Vector... also carry .wrapped: match types, not that.
    if isinstance(value, BoundBox):
        return {"bbox": [_num(v) for v in (*value.min, *value.max)]}
    if isinstance(value, Shape):
        return {"shape": shape_sig(value)}
    if isinstance(value, (list, tuple)):
        return [_canon(v) for v in value]
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise Uncacheable(f"dict with non-str keys: {value!r:.80}")
        return {k: _canon(v) for k, v in sorted(value.items())}
    raise Uncacheable(f"no canonical form for {type(value).__qualname__}")


def _exclusion(e):
    if hasattr(e, "wrapped"):
        return {"shape": shape_sig(e)}
    if hasattr(e, "is_inside"):
        cls = type(e)
        try:
            source = inspect.getsource(cls)
            state = vars(e)
        except (OSError, TypeError) as exc:
            raise Uncacheable(f"predicate {cls.__qualname__}: {exc}") from exc
        return {"predicate": f"{cls.__module__}.{cls.__qualname__}",
                "source": hashlib.sha256(source.encode()).hexdigest(),
                "vars": _canon(state)}
    if isinstance(e, (tuple, list)) and len(e) == 6:
        return {"box": [_num(v) for v in e]}
    raise Uncacheable(f"exclusion of type {type(e).__qualname__}")


def _sorted(items):
    return sorted(items, key=lambda c: json.dumps(c, sort_keys=True))


def _args(orientation, cutters, exclusions, model, print_frame) -> dict:
    from build123d import Location

    if print_frame is not None and not isinstance(print_frame, Location):
        raise Uncacheable(f"print_frame of type {type(print_frame).__qualname__}")
    frame = None
    if print_frame is not None:
        # Euler degeneracy can only split one rotation into two keys (a
        # spurious miss), never merge two rotations (a false hit).
        frame = [[_num(v) for v in print_frame.position],
                 [_num(v) for v in print_frame.orientation]]
    boxes = []
    for c in cutters:
        if not hasattr(c, "bounding_box"):
            raise Uncacheable(f"cutter of type {type(c).__qualname__}")
        # _cutter_boxes reduces each cutter to the bbox of what it receives:
        # the print_frame-moved cutter (a rotated bbox is not the bbox of the
        # rotated shape), so key exactly that box.
        bb = (print_frame * c if print_frame is not None else c).bounding_box()
        boxes.append([_num(v) for v in (*bb.min, *bb.max)])
    if not isinstance(model, str):
        raise Uncacheable(f"model label of type {type(model).__qualname__}")
    return {"orientation": [_num(v) for v in orientation],
            "cutters": _sorted(boxes),
            "exclusions": _sorted(_exclusion(e) for e in exclusions),
            "model": model,
            "print_frame": frame}


def key(part, orientation=(0.0, 0.0, 1.0), *, cutters=(), exclusions=(), model="part",
        print_frame=None) -> str:
    """The cache key for one audit() call; raises Uncacheable."""
    if getattr(part, "wrapped", None) is None:
        raise Uncacheable(f"part of type {type(part).__qualname__}")
    h = hashlib.sha256()
    for component in (
        shape_sig(part),
        {"source": _source_hash(), "thresholds": _thresholds()},
        _versions(),
        _args(orientation, list(cutters), list(exclusions), model, print_frame),
    ):
        h.update(json.dumps(component, sort_keys=True).encode())
        h.update(b"\0")
    return h.hexdigest()


# --- store ----------------------------------------------------------------

def _to_json(report) -> dict:
    return dataclasses.asdict(report)


def _retuple(value):
    if isinstance(value, list):
        return tuple(_retuple(v) for v in value)
    return value


def _from_json(data: dict):
    from tests.print_audit import DownwardFillet, PrintAuditReport

    names = {f.name for f in dataclasses.fields(PrintAuditReport)}
    if set(data) != names:
        raise ValueError(f"stored fields {sorted(data)} != {sorted(names)}")
    fields = {name: _retuple(v) for name, v in data.items()
              if name != "downward_fillets"}
    fields["downward_fillets"] = tuple(
        DownwardFillet(**{k: _retuple(v) for k, v in d.items()})
        for d in data["downward_fillets"])
    return PrintAuditReport(**fields)


def load(path: Path):
    """The stored report at ``path``, or None (absent, corrupt, unreadable)."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        log.warning("audit cache: unreadable %s (%s); treating as a miss", path, exc)
        return None
    try:
        data = json.loads(text)
        if data.get("key") != path.stem:
            raise ValueError("key mismatch")
        return _from_json(data["report"])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        log.warning("audit cache: corrupt %s (%s); treating as a miss", path, exc)
        return None


def store(path: Path, report) -> None:
    """Write atomically (xdist workers may store the same key at once)."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"key": path.stem, "report": _to_json(report)},
                                  sort_keys=True, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink()
        log.warning("audit cache: could not store %s (%s)", path, exc)


def _run(fn, counter, *args, **kwargs):
    start = time.process_time()
    report = fn(*args, **kwargs)
    if counter == "misses":
        COUNTS["audit_s"] += time.process_time() - start
    COUNTS[counter] += 1
    return report


def cached(fn, part, orientation, *, cutters, exclusions, model, print_frame):
    """``fn(part, orientation, ...)`` answered from the store when possible.
    Stores only after ``fn`` returns (an audit that raises stores nothing)."""
    kwargs = dict(cutters=cutters, exclusions=exclusions, model=model,
                  print_frame=print_frame)
    directory = cache_dir()
    if directory is None:
        return _run(fn, "off", part, orientation, **kwargs)
    try:
        path = directory / f"{key(part, orientation, **kwargs)}.json"
    except Uncacheable as exc:
        log.info("audit cache: uncacheable call (%s)", exc)
        return _run(fn, "off", part, orientation, **kwargs)
    report = load(path)
    if report is not None:
        COUNTS["hits"] += 1
        return report
    report = _run(fn, "misses", part, orientation, **kwargs)
    store(path, report)
    return report


def summary(counts=None) -> str:
    c = COUNTS if counts is None else counts
    return (f"AUDIT-CACHE hits={c['hits']} misses={c['misses']} off={c['off']} "
            f"audit_s={c['audit_s']:.1f}")
