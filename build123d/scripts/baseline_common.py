"""Shared numerical contract for the BREP, bake and audit-row baselines."""
import json
import math
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tests" / "baselines"
# First matching field rule wins. Audit numbers retain the spike's native-unit
# absolute join; only BREP volume uses relative tolerance.
TOLERANCES = {
    "geometry.volume": ("relative", 1e-6),
    "bake.volume_mm3": ("absolute", 1e-6),
    "geometry.*": ("absolute", 1e-6),
    "bake.*": ("absolute", 1e-6),
    "audit-rows.*": ("absolute", 1e-6),
    "discrete": ("exact", 0),
}


def tolerance(kind, field, before, after):
    # Inventory counts, topology, booleans and strings are always exact.
    if isinstance(before, bool) or isinstance(after, bool):
        return TOLERANCES["discrete"]
    if isinstance(before, int) or isinstance(after, int):
        return TOLERANCES["discrete"]
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return TOLERANCES["discrete"]
    return TOLERANCES.get(f"{kind}.{field}", TOLERANCES[f"{kind}.*"])


def normalized(value):
    """Stable nine-decimal JSON floats; reject non-finite measurements."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite measurement: {value}")
        return round(value, 9) or 0.0
    if isinstance(value, dict):
        return {k: normalized(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    return value


def write_json(path, value):
    def render(item, level=0):
        indent = "  " * (level + 1)
        if isinstance(item, dict):
            children = [json.dumps(k) + ": " + render(v, level + 1)
                        for k, v in item.items()]
            opening, closing = "{", "}"
        elif isinstance(item, list):
            children = [render(v, level + 1) for v in item]
            opening, closing = "[", "]"
        elif isinstance(item, float):
            return format(item, ".9f")
        else:
            return json.dumps(item, allow_nan=False)
        if not children:
            return opening + closing
        return opening + "\n" + indent + (",\n" + indent).join(children) + "\n" + "  " * level + closing

    content = render(normalized(value)) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as temporary:
        temporary.write(content)
    temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def read_baseline(kind, path=None):
    path = path or BASELINES / kind / f"{kind}-baseline.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc["header"]["schema_version"] != 1 or doc["header"]["kind"] != kind:
        raise ValueError(f"wrong baseline schema/kind: {path}")
    return doc


def load_waivers(path=None):
    doc = json.loads((path or BASELINES / "waivers.json").read_text(encoding="utf-8"))
    seen = set()
    for entry in doc["waivers"]:
        for key in ("kind", "path", "reason", "bead"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError(f"waiver needs nonempty {key}: {entry}")
        if entry["kind"] not in ("geometry", "bake", "audit-rows"):
            raise ValueError(f"unknown waiver kind: {entry}")
        key = (entry["kind"], entry["path"])
        if key in seen:
            raise ValueError(f"duplicate waiver: {key}")
        seen.add(key)
    return doc["waivers"]


def compare(kind, expected, actual, waivers=()):
    """Return (failures, waived); paths are JSON pointers, without wildcards."""
    failures, waived = [], []
    waiver_map = {w["path"]: w for w in waivers if w["kind"] == kind}

    def visit(a, b, path="", field=""):
        waiver = waiver_map.get(path)
        if waiver:
            waived.append(f"{path}: WAIVED ({waiver['bead']}: {waiver['reason']})")
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                child = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
                if key not in a or key not in b:
                    waiver = waiver_map.get(child)
                    if waiver:
                        waived.append(f"{child}: WAIVED ({waiver['bead']}: {waiver['reason']})")
                    else:
                        failures.append(f"{child}: {'unexpected' if key not in a else 'missing'}")
                else:
                    visit(a[key], b[key], child, key)
            return
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                failures.append(f"{path}: length {len(a)} -> {len(b)} (exact)")
            for i, (old, new) in enumerate(zip(a, b)):
                visit(old, new, f"{path}/{i}", field)
            return
        mode, limit = tolerance(kind, field, a, b)
        if mode == "exact":
            equal = type(a) is type(b) and a == b
        else:
            equal = math.isfinite(a) and math.isfinite(b) and (
                abs(a - b) <= (limit * abs(a) if mode == "relative" else limit))
        if not equal:
            failures.append(f"{path}: {a!r} -> {b!r} ({mode} {limit:g})")

    visit(expected, actual)
    return failures, waived


def report(kind, expected, actual, waivers):
    failures, waived = compare(kind, expected, actual, waivers)
    for line in waived + failures:
        print(line)
    print(f"{kind}: {'FAIL' if failures else 'PASS'}; "
          f"{len(failures)} differences, {len(waived)} waivers")
    return int(bool(failures))
