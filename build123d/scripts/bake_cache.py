"""Content-addressed preset bake cache (bead pst-aqza2). Stdlib only.

A production build re-bakes only the presets whose INPUTS changed; every
other preset is restored byte-for-byte from a tarball the Blob store
(scripts/bd-bake-cache.mjs) keeps under

    bd-bake-cache/v<SCHEMA>/<key>/<slug>-<preset>.tar.gz

Key (one per preset) = sha256 over: SCHEMA; the interpreter + platform;
uv.lock + pyproject.toml; every file in the static import closure of
scripts/export.py and of the model's module (an AST walk over files under
build123d/, discovery edges out of holders/registry.py excluded); the
data set (DATA_GLOBS); and the preset id + resolved values as sorted JSON.
Editing another model, a test or a doc leaves the key alone.

Coverage is self-enforcing: with the audit armed, a sys.addaudithook
records every file opened under build123d/ and the bake fails, after the
last preset, naming each read the key did not cover. The hook only sees
Python-level opens: a read made inside native OCCT/OCP code is invisible
to it (the data set already holds every non-Python tree such code could be
handed a path to).
"""
from __future__ import annotations

import ast
import gzip
import hashlib
import io
import json
import os
import platform
import sys
import tarfile
from pathlib import Path

SCHEMA = 1
BD_ROOT = Path(__file__).resolve().parent.parent
CACHE_PREFIX = f"bd-bake-cache/v{SCHEMA}"

# Non-Python files a bake can read (all model presets share them).
# manifest.json is deliberately NOT here: the bake never reads it (the audit
# would fail if it did), and it changes on every new model or preset, which
# would invalidate every key.
DATA_GLOBS = ("assets/**/*", "profiles/**/*", "labels/*.json", "reference/measured/**/*")
LOCK_FILES = ("uv.lock", "pyproject.toml")
# Never inputs: the environment, the bake's own output, bytecode caches.
IGNORED_PARTS = {".venv", "baked", "__pycache__"}
# sys.path[0] is scripts/ when export.py runs as a script.
_IMPORT_ROOTS = ("", "scripts")


def _ignored(rel: Path) -> bool:
    return any(part in IGNORED_PARTS for part in rel.parts)


def _resolve_module(name: str, root: Path) -> list[Path]:
    """Files executed by importing dotted ``name`` from under root: each
    package __init__ on the way plus the module itself. [] when external."""
    parts = name.split(".")
    for base in _IMPORT_ROOTS:
        here = root / base if base else root
        found: list[Path] = []
        for i, part in enumerate(parts):
            here = here / part
            if (here / "__init__.py").is_file():
                found.append(here / "__init__.py")
            elif i == len(parts) - 1 and here.with_suffix(".py").is_file():
                found.append(here.with_suffix(".py"))
            elif not here.is_dir():  # a dir without __init__ is a namespace package
                found = []
                break
        if found:
            return found
    return []


def _package_of(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    return parts if path.name == "__init__.py" else parts[:-1]


def _imports(path: Path, root: Path) -> list[str]:
    """Every dotted module name ``path`` imports, at any nesting depth
    (function-local imports included), relative imports made absolute."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package = _package_of(path, root)
                base = package[: len(package) - node.level + 1]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            if mod:
                names.append(mod)
            # `from pkg import sub` may name a submodule.
            names.extend(f"{mod}.{alias.name}" if mod else alias.name for alias in node.names)
    return names


def import_closure(entries: list[Path], root: Path = BD_ROOT,
                   skip_edges: dict[Path, set[Path]] | None = None) -> set[Path]:
    """Every file under root reachable from ``entries`` by static imports.

    skip_edges maps an importing file to targets whose edge is ignored —
    used for holders/registry.py's all_models() discovery imports, which
    register every model but feed none of them into another's build."""
    skip_edges = skip_edges or {}
    seen: set[Path] = set()
    todo = [p.resolve() for p in entries]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        for name in _imports(path, root):
            for target in _resolve_module(name, root):
                target = target.resolve()
                if target not in seen and target not in skip_edges.get(path, ()):
                    todo.append(target)
    return seen


def data_files(root: Path = BD_ROOT) -> set[Path]:
    files: set[Path] = set()
    for pattern in DATA_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and not _ignored(path.relative_to(root)):
                files.add(path.resolve())
    return files


def _digest(files: set[Path], root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(files, key=lambda p: p.relative_to(root).as_posix()):
        h.update(path.relative_to(root).as_posix().encode() + b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


class KeyBuilder:
    """Per-preset keys for one tree. ``model_modules`` maps each registered
    model's module file to itself; registry edges into them are discovery."""

    def __init__(self, root: Path, export_entry: Path, registry: Path,
                 model_modules: set[Path]):
        self.root = root.resolve()
        self.registry = registry.resolve()
        self.model_modules = {p.resolve() for p in model_modules}
        self._skip = {self.registry: self.model_modules}
        self.export_closure = import_closure([export_entry], self.root, self._skip)
        self.data = data_files(self.root)
        self.locks = {(self.root / f).resolve() for f in LOCK_FILES if (self.root / f).is_file()}
        self._shared = hashlib.sha256(json.dumps({
            "schema": SCHEMA,
            "python": sys.version,
            "machine": platform.machine(),
            "system": platform.system(),
            "locks": _digest(self.locks, self.root),
            "data": _digest(self.data, self.root),
        }, sort_keys=True).encode()).hexdigest()
        self._closures: dict[Path, set[Path]] = {}

    def closure(self, module_file: Path) -> set[Path]:
        module_file = module_file.resolve()
        if module_file not in self._closures:
            self._closures[module_file] = self.export_closure | import_closure(
                [module_file], self.root, self._skip)
        return self._closures[module_file]

    def inputs(self, module_file: Path) -> set[Path]:
        """Every file the key of a preset of this model covers."""
        return self.closure(module_file) | self.data | self.locks

    def key(self, module_file: Path, preset_id: str, values: dict) -> str:
        return hashlib.sha256(json.dumps({
            "shared": self._shared,
            "code": _digest(self.closure(module_file), self.root),
            "preset": preset_id,
            "values": values,
        }, sort_keys=True, default=repr).encode()).hexdigest()


class ReadAudit:
    """Records files opened under root (sys.addaudithook; cannot be removed,
    so ``active`` gates it). ``take()`` returns and clears the window."""

    def __init__(self, root: Path = BD_ROOT):
        self.root = root.resolve()
        self.active = True
        self._reads: set[Path] = set()
        sys.addaudithook(self._hook)

    def _hook(self, event: str, args: tuple) -> None:
        if not self.active or event != "open" or not args:
            return
        target = args[0]
        if isinstance(target, int) or target is None:
            return
        try:
            path = Path(os.fsdecode(target))
            path = (path if path.is_absolute() else Path.cwd() / path).resolve()
            rel = path.relative_to(self.root)
        except (ValueError, OSError, TypeError):
            return
        if not _ignored(rel) and path.is_file():
            self._reads.add(path)

    def take(self) -> set[Path]:
        reads, self._reads = self._reads, set()
        return reads


def uncovered(reads: set[Path], inputs: set[Path]) -> list[Path]:
    return sorted(reads - inputs)


# ── Tarballs ────────────────────────────────────────────────────────────

def tar_name(slug: str, preset_id: str) -> str:
    return f"{slug}-{preset_id}.tar.gz"


def blob_pathname(key: str, slug: str, preset_id: str) -> str:
    return f"{CACHE_PREFIX}/{key}/{tar_name(slug, preset_id)}"


def pack(files: list[Path]) -> bytes:
    """A deterministic gzip tarball of ``files`` (flat, by basename)."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path in sorted(files, key=lambda p: p.name):
            info = tarfile.TarInfo(path.name)
            data = path.read_bytes()
            info.size, info.mtime, info.mode = len(data), 0, 0o644
            tar.addfile(info, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(raw.getvalue())
    return out.getvalue()


def allowed_member(name: str, preset_id: str, required: list[str], multi_colour: bool) -> bool:
    if name in required:
        return True
    # Per-colour part STLs: names come from the build, so only the shape is known.
    return (multi_colour and name.startswith(f"{preset_id}-") and name.endswith(".stl")
            and "/" not in name and name not in (".", ".."))


def unpack(blob: bytes, model_dir: Path, preset_id: str, required: list[str],
           multi_colour: bool) -> list[str]:
    """Extract a cached preset into model_dir; returns the member names.

    Raises ValueError (→ a miss) unless the tarball holds every required file,
    nothing outside the preset's own file shapes, and only regular files.
    Members are validated BEFORE anything is written."""
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
            members = tar.getmembers()
            names = [m.name for m in members]
            if len(set(names)) != len(names):
                raise ValueError("duplicate members")
            for m in members:
                if not m.isfile() or not allowed_member(m.name, preset_id, required, multi_colour):
                    raise ValueError(f"unexpected member {m.name!r}")
            missing = sorted(set(required) - set(names))
            if missing:
                raise ValueError(f"missing {', '.join(missing)}")
            payload = {m.name: tar.extractfile(m).read() for m in members}
    except (tarfile.TarError, OSError, EOFError) as error:
        raise ValueError(f"unreadable tarball: {error}") from error
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, data in payload.items():
        (model_dir / name).write_bytes(data)
    return sorted(names)
