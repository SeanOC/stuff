"""``bd build``: build a registered model once into a cached BREP (pst-ptl41 C1).

The cache entry is ``<cache>/<key>.brep`` (the part in MODEL coordinates,
exactly what ``spec.build(values)`` returned) plus ``<key>.json`` (slug,
params, versions, source hash, bbox, volume, build seconds). Every query
subcommand reads the BREP instead of rebuilding.

KEY = sha256 over slug + canonical resolved params + the audit cache's
version tuple + a SOURCE HASH of every first-party file under build123d/
(any extension: builders read .json/.ttf/.stl at runtime) except the
non-geometry trees and the generated trees below. Editing or regenerating
any hashed file moves the key, so a stale BREP is never served.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # build123d/
DEFAULT_CACHE = ROOT / ".cache" / "parts"

# Top-level trees that carry no geometry: tooling, tests, docs, provenance.
NON_GEOMETRY = frozenset(
    {"bd", "tests", "scripts", "ci", "reference", "viewer", "tools", "docs"})
# Generated trees. .cache/ holds the BREPs this key names (and the audit
# cache); baked/ is the scripts/export.py --presets-only mesh bake; out/ is
# scripts/export.py's output. All three are gitignored (build123d/.gitignore).
GENERATED_TOP = frozenset({".cache", "baked", "out"})
GENERATED_SUFFIXES = (".pyc", ".pyo")

KEY_RE = re.compile(r"[0-9a-f]{64}")


class UsageError(Exception):
    """A bad slug, preset, param or key: the CLI exits 2 with this text."""


def cache_dir() -> Path:
    env = os.environ.get("BD_PART_CACHE", "")
    return Path(env) if env else DEFAULT_CACHE


# --- key ------------------------------------------------------------------

def _hashed(rel: Path) -> bool:
    """Whether the file at ``rel`` (relative to the hashed root) is hashed."""
    parts = rel.parts
    if parts[0] in NON_GEOMETRY or parts[0] in GENERATED_TOP:
        return False
    # __pycache__ anywhere; any dot-directory (.venv, .pytest_cache, ...) is
    # an environment or tool cache, never a builder input.
    if any(p == "__pycache__" or p.startswith(".") for p in parts[:-1]):
        return False
    return not rel.name.endswith(GENERATED_SUFFIXES)


def hashed_files(root: Path = ROOT) -> list[Path]:
    """Every hashed file under ``root``, sorted by relative path."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        # Prune excluded trees so a 700 MB .venv is never walked.
        dirnames[:] = [d for d in dirnames
                       if not (rel_dir == Path(".") and (d in NON_GEOMETRY or d in GENERATED_TOP))
                       and d != "__pycache__" and not d.startswith(".")]
        for name in filenames:
            rel = rel_dir / name
            if _hashed(rel):
                out.append(rel)
    return sorted(out, key=lambda p: p.as_posix())


def source_hash(root: Path = ROOT) -> str:
    """sha256 of relative path + bytes of every hashed file under ``root``
    (the whole-tree analogue of tests/audit_cache.py _source_hash)."""
    h = hashlib.sha256()
    for rel in hashed_files(root):
        h.update(rel.as_posix().encode() + b"\0")
        h.update((root / rel).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def versions() -> dict:
    from tests.audit_cache import _versions

    return _versions()


def part_key(name: str, values: dict, *, root: Path = ROOT,
             source: str | None = None) -> str:
    h = hashlib.sha256()
    for component in (name, values, versions(),
                      source if source is not None else source_hash(root)):
        h.update(json.dumps(component, sort_keys=True).encode())
        h.update(b"\0")
    return h.hexdigest()


# --- resolution -----------------------------------------------------------

def find_spec(slug: str):
    """The registered ModelSpec for ``slug`` (manifest slug or spec name)."""
    from holders.registry import all_models

    specs = all_models()
    for spec in specs:
        if slug in (spec.name, spec.slug):
            return spec
    names = ", ".join(sorted(s.slug for s in specs))
    raise UsageError(f"unknown model {slug!r}; known: {names}")


def _parse_value(param, raw: str):
    """A --param string as the param's kind; resolve_values validates it."""
    if param.kind == "boolean":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise UsageError(f"{param.name}: expected true/false, got {raw!r}")
    if param.kind in ("number", "integer"):
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            raise UsageError(f"{param.name}: expected a number, got {raw!r}") from None
    return raw


def resolve(slug: str, preset: str | None, params: list[str]):
    """(spec, preset id or None, resolved values). Raises UsageError."""
    spec = find_spec(slug)
    overrides: dict = {}
    if preset is not None:
        match = next((p for p in spec.presets if p.id == preset), None)
        if match is None:
            ids = ", ".join(p.id for p in spec.presets) or "(none)"
            raise UsageError(f"{spec.name}: unknown preset {preset!r}; presets: {ids}")
        overrides.update(match.values)
    by_name = {p.name: p for p in spec.params}
    for item in params:
        name, sep, raw = item.partition("=")
        if not sep:
            raise UsageError(f"--param expects k=v, got {item!r}")
        param = by_name.get(name)
        if param is None:
            # resolve_values names the unknown param in the model's own words.
            overrides[name] = raw
        else:
            overrides[name] = _parse_value(param, raw)
    try:
        values = spec.resolve_values(overrides)
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    return spec, preset, values


# --- store ----------------------------------------------------------------

@dataclass
class Entry:
    key: str
    meta: dict
    hit: bool

    @property
    def brep(self) -> Path:
        return cache_dir() / f"{self.key}.brep"

    def load(self):
        from build123d import import_brep

        return import_brep(str(self.brep))


def _bbox(shape) -> dict:
    bb = shape.bounding_box()
    return {"min": [round(v, 6) for v in bb.min],
            "max": [round(v, 6) for v in bb.max],
            "size": [round(v, 6) for v in bb.size]}


def _write_atomic(path: Path, write) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    write(tmp)
    os.replace(tmp, path)


def lookup(key: str) -> Entry:
    """The cache entry for an explicit key (query form). Raises UsageError."""
    meta_path = cache_dir() / f"{key}.json"
    if not (meta_path.exists() and (cache_dir() / f"{key}.brep").exists()):
        raise UsageError(f"no cached part {key} in {cache_dir()}; "
                         "run `uv run python -m bd build <slug>` first")
    return Entry(key, json.loads(meta_path.read_text()), hit=True)


def build(slug: str, preset: str | None = None, params: list[str] = (),
          *, rebuild: bool = False) -> Entry:
    """Build (or find) the cached BREP for slug/preset/params."""
    from build123d import export_brep

    spec, preset, values = resolve(slug, preset, list(params))
    source = source_hash()
    key = part_key(spec.name, values, source=source)
    directory = cache_dir()
    if not rebuild:
        try:
            entry = lookup(key)
            return entry
        except UsageError:
            pass
    start = time.process_time()
    try:
        part = spec.build(values)
    except ValueError as exc:
        # C3: the model's own rejection of a value is a usage error.
        raise UsageError(f"{spec.name}: {exc}") from None
    seconds = time.process_time() - start
    meta = {
        "key": key, "slug": spec.slug, "model": spec.name, "preset": preset,
        "params": values, "versions": versions(), "source_hash": source,
        "bbox": _bbox(part), "volume": round(part.volume, 6),
        "build_s": round(seconds, 3),
    }
    directory.mkdir(parents=True, exist_ok=True)
    _write_atomic(directory / f"{key}.brep", lambda p: export_brep(part, str(p)))
    _write_atomic(directory / f"{key}.json",
                  lambda p: p.write_text(json.dumps(meta, indent=2, sort_keys=True)))
    return Entry(key, meta, hit=False)


def entry_for(target: str, preset: str | None, params: list[str], *,
              rebuild: bool = False) -> Entry:
    """A query's part: ``target`` is a cache key, or a slug to build first."""
    if KEY_RE.fullmatch(target):
        if preset is not None or params or rebuild:
            raise UsageError("--preset/--param/--rebuild apply to a slug, not a key")
        return lookup(target)
    return build(target, preset, params, rebuild=rebuild)


def run(args) -> tuple[int, str, dict]:
    entry = build(args.slug, args.preset, args.param, rebuild=args.rebuild)
    m = entry.meta
    size = " × ".join(f"{v:.1f}" for v in m["bbox"]["size"])
    summary = (f"{entry.key}  {m['model']}"
               f"{'/' + m['preset'] if m['preset'] else ''}  "
               f"{'HIT' if entry.hit else 'BUILT'}  {size} mm  "
               f"{m['volume']:.1f} mm³  build {m['build_s']:.1f} s")
    return 0, summary, {"key": entry.key, "hit": entry.hit,
                        "brep": str(entry.brep), **m}
