"""Model registry — the contract between models and the export/test harness.

Register every buildable artifact here. The export harness (scripts/export.py),
the manifest emitter (scripts/manifest.py), and the test suite (tests/)
iterate this registry, so a new model gets STL+GLB+PNG export, manifest
entry, and mesh sanity tests for free by registering itself.

App contract
------------
``Param`` and ``Preset`` mirror the web app's shapes in
``lib/scad-params/parse.ts`` (Param/ParamValue/Preset) EXACTLY — the
manifest emitter serializes them verbatim so the app can ingest
``build123d/manifest.json`` without translation. Base fields are
``name, label?, group?, unit?``; ``EnumParam`` carries ``choices``
(not "options"); presets are ``{id, label, values}``.

``tags`` containing ``"smoke"`` marks toolchain smoke artifacts: they
stay registered (the harness still builds + tests them) but are
excluded from the app-facing manifest and from ``--presets-only``
baking, which cover app-listed models only.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from build123d import Location, Part

# URL-safe id: alphanumeric start, then alphanumerics, '-', '_'. Used for
# model slugs and preset ids (both end up in file paths / URL segments).
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

# Mount types a model may declare via ``ModelSpec.mounts``. Each must have a
# deterministic geometry contract in tests/mount_contracts.py (the contract
# module asserts full coverage at import). A model tagged with an unknown
# mount fails loudly at registration (see _validate_spec). Add a new mount
# type here AND its contract together.
KNOWN_MOUNTS: frozenset[str] = frozenset({"multiconnect-slot"})

# Mirrors MODEL_CATEGORIES ids in lib/models/catalog.ts (app catalog
# contract). Keep in sync when a category is added there.
CATEGORY_IDS: frozenset[str] = frozenset(
    {"storage", "multiboard", "toys", "household"}
)

ParamValue = float | int | bool | str


@dataclass(frozen=True)
class Param:
    """One tunable. Mirrors lib/scad-params/parse.ts Param exactly.

    kind:
      "number"  -> default: int|float (not bool), optional min/max/step
      "integer" -> default: int (not bool), optional min/max/step
      "boolean" -> default: bool
      "string"  -> default: str
      "enum"    -> default: str in choices; choices: non-empty tuple[str]
    """

    name: str
    kind: str  # "number" | "integer" | "boolean" | "string" | "enum"
    default: ParamValue
    label: str | None = None
    group: str | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class Preset:
    """Named parameter set. Mirrors lib/scad-params/parse.ts Preset exactly.

    id: unique within the model, URL-safe (used in baked file paths).
    label: required, human-readable (displayed in the preset rail).
    values: param-name -> value; every key must be a registered param of
    this model, every value kind-consistent (see _validate_value).
    """

    id: str
    label: str
    values: dict[str, ParamValue]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_value(kind: str, name: str, value: Any) -> str | None:
    """Return an error string if value is not kind-consistent, else None."""
    if kind in ("number", "integer"):
        if not _is_number(value):
            return f"{name}: expected number, got {type(value).__name__}"
        if kind == "integer" and isinstance(value, float):
            return f"{name}: integer param expects int, got float {value!r}"
        if kind == "integer" and value != int(value):
            return f"{name}: integer param value {value} is not whole"
    elif kind == "boolean":
        if not isinstance(value, bool):
            return f"{name}: expected boolean, got {type(value).__name__}"
    elif kind in ("string", "enum"):
        if not isinstance(value, str):
            return f"{name}: expected string, got {type(value).__name__}"
    else:  # pragma: no cover - registered kinds only
        return f"{name}: unknown param kind {kind!r}"
    return None


def _validate_param(param: Param) -> str | None:
    if not param.name or not SAFE_ID_RE.match(param.name):
        return f"param {param.name!r}: name must be a non-empty safe identifier"
    if param.kind not in ("number", "integer", "boolean", "string", "enum"):
        return f"param {param.name!r}: unknown kind {param.kind!r}"
    for field in ("label", "group", "unit"):
        value = getattr(param, field)
        if value is not None and (not isinstance(value, str) or not value):
            return f"param {param.name!r}: {field} must be a non-empty string"
    if param.kind in ("number", "integer"):
        for bound in ("min", "max", "step"):
            value = getattr(param, bound)
            if value is not None and not _is_number(value):
                return f"param {param.name!r}: {bound} must be a number"
        if param.min is not None and param.max is not None and param.min > param.max:
            return f"param {param.name!r}: min {param.min} > max {param.max}"
        if param.step is not None and param.step <= 0:
            return f"param {param.name!r}: step must be > 0"
        if not _validate_value(param.kind, param.name, param.default):
            return None
        if param.min is not None and param.default < param.min:
            return f"param {param.name!r}: default {param.default} < min {param.min}"
        if param.max is not None and param.default > param.max:
            return f"param {param.name!r}: default {param.default} > max {param.max}"
        return None
    if param.kind == "enum":
        if not param.choices or any(
            not isinstance(c, str) or not c for c in param.choices
        ):
            return f"param {param.name!r}: enum choices must be a non-empty tuple of strings"
        if len(set(param.choices)) != len(param.choices):
            return f"param {param.name!r}: duplicate enum choices"
        if not isinstance(param.default, str) or param.default not in param.choices:
            return (
                f"param {param.name!r}: default {param.default!r} "
                f"not in choices {list(param.choices)}"
            )
        return None
    return _validate_value(param.kind, param.name, param.default)


@dataclass
class MountFixtures:
    """Library-geometry fixtures for one mount instance on a model.

    Returned by a model module's ``mount_fixtures(mount_type, values)`` hook
    and consumed by the deterministic mount contracts (tests/mount_contracts
    .py). Everything here is 100% opengrid library geometry, positioned in
    the model's own coordinate frame — the contract needs nothing bespoke,
    so a new model inherits the whole contract suite just by supplying this.

    cutters:    the placed library slot cutters (the pockets carved into the
                model's back plate). Prove the entry aperture is at the plate
                bottom face — a sealed pocket removes nothing there.
    seat_locs:  one world ``Location`` per slot; ``loc * RoundHead()`` is a
                real library round head at its seated (fully-inserted) pose.
    entry_axis: unit direction a wall head travels as the holder lowers onto
                it and the head rides to the seat. The channel opening faces
                ``-entry_axis``. Currently the contracts assume ``(0, 0, 1)``.
    face_normal: outward unit normal of the mount (board-facing) face — the
                direction a seated head would travel to pull straight off the
                wall. The retention contract drives each seated head along
                this axis and requires it to FOUL the plate (the narrow lip
                holds the head's wide flange). Distinct from ``entry_axis``:
                the head slides IN along ``+entry_axis`` but is retained
                across ``face_normal`` (the dovetail taper axis). Defaults to
                ``(0, -1, 0)`` (the -Y board side).
    """

    cutters: list[Part]
    seat_locs: list[Location]
    entry_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    face_normal: tuple[float, float, float] = (0.0, -1.0, 0.0)


@dataclass(frozen=True)
class ModelSpec:
    """A registered buildable artifact.

    name:    artifact basename / registry key, e.g. "holder_spray_can".
             The app-facing slug is name with '_' -> '-'.
    build:   build(values) -> Part. ``values`` is a resolved param dict
             (see resolve_values); smoke models ignore it.
    tags:    "smoke" marks toolchain smoke artifacts (excluded from the
             app-facing manifest and --presets-only baking).
    params:  typed params (see Param); order defines manifest order.
    presets: named preset value sets (see Preset).
    title:   app-facing title; falls back to a humanized slug when empty.
    category_id: app catalog category (see CATEGORY_IDS); required for
             app-listed (non-smoke) models.
    """

    name: str
    build: Callable[[dict[str, Any]], Part]
    description: str = ""
    tags: tuple[str, ...] = ()
    params: tuple[Param, ...] = ()
    presets: tuple[Preset, ...] = ()
    title: str = ""
    category_id: str = ""
    # Mount types this model carries (see KNOWN_MOUNTS). The test harness
    # auto-parametrizes the deterministic mount contracts over every model
    # with a non-empty ``mounts``, so future models inherit mount
    # verification for free. A model declaring a mount must expose a
    # ``mount_fixtures(mount_type, values)`` hook in its module.
    mounts: tuple[str, ...] = ()
    # Print orientation: the unit vector, IN THIS MODEL'S OWN COORDINATE
    # FRAME, that points UP (away from the build plate) in the declared
    # print pose. The default ``(0, 0, 1)`` means "printed as modelled, +Z
    # up"; a model that prints on another face declares the axis that ends
    # up pointing up (a holder printed back-plate-down on its −Y face would
    # declare ``(0, 1, 0)``). The deterministic print audit
    # (tests/print_audit.py) measures overhangs/bridges/walls against this.
    # Additive with a backward-compatible default — not serialized into
    # manifest.json (scripts/manifest.py emits an explicit field list). A
    # production model declares a non-default orientation only once it passes
    # the audit at that orientation (design-guidelines §6 items 1–3).
    print_orientation: tuple[float, float, float] = (0.0, 0.0, 1.0)

    @property
    def slug(self) -> str:
        # Same rule as lib/models/discover.ts stemToSlug.
        return self.name.replace("_", "-")

    @property
    def is_smoke(self) -> bool:
        return "smoke" in self.tags

    def param_names(self) -> frozenset[str]:
        return frozenset(p.name for p in self.params)

    def default_values(self) -> dict[str, ParamValue]:
        return {p.name: p.default for p in self.params}

    def resolve_values(
        self, overrides: dict[str, Any] | None = None
    ) -> dict[str, ParamValue]:
        """Defaults + overrides, every value validated against its param.

        Raises ValueError on unknown param names, kind mismatches, enum
        values outside choices, or values outside declared min/max —
        fail loud here, not mid-build.
        """
        values = self.default_values()
        by_name = {p.name: p for p in self.params}
        for name, value in (overrides or {}).items():
            param = by_name.get(name)
            if param is None:
                raise ValueError(f"{self.name}: unknown param {name!r}")
            error = _validate_value(param.kind, name, value)
            if error:
                raise ValueError(f"{self.name}: {error}")
            if param.kind == "enum" and value not in param.choices:
                raise ValueError(
                    f"{self.name}: {name}={value!r} not in choices {list(param.choices)}"
                )
            if param.kind in ("number", "integer"):
                if param.min is not None and value < param.min:
                    raise ValueError(
                        f"{self.name}: {name}={value} < min {param.min}"
                    )
                if param.max is not None and value > param.max:
                    raise ValueError(
                        f"{self.name}: {name}={value} > max {param.max}"
                    )
            values[name] = value
        return values


_REGISTRY: dict[str, ModelSpec] = {}


def _validate_preset(spec: ModelSpec, preset: Preset) -> str | None:
    if not preset.id or not SAFE_ID_RE.match(preset.id):
        return f"{spec.name}: preset id {preset.id!r} must be URL-safe"
    if not preset.label:
        return f"{spec.name}: preset {preset.id!r}: label is required"
    by_name = {p.name: p for p in spec.params}
    for name, value in preset.values.items():
        param = by_name.get(name)
        if param is None:
            return (
                f"{spec.name}: preset {preset.id!r} references unknown param {name!r}"
            )
        error = _validate_value(param.kind, name, value)
        if error:
            return f"{spec.name}: preset {preset.id!r}: {error}"
        if param.kind == "enum" and value not in param.choices:
            return (
                f"{spec.name}: preset {preset.id!r}: {name}={value!r} "
                f"not in choices {list(param.choices)}"
            )
        if param.kind in ("number", "integer"):
            if param.min is not None and value < param.min:
                return f"{spec.name}: preset {preset.id!r}: {name}={value} < min {param.min}"
            if param.max is not None and value > param.max:
                return f"{spec.name}: preset {preset.id!r}: {name}={value} > max {param.max}"
    return None


def _validate_spec(spec: ModelSpec) -> str | None:
    if not spec.name or not SAFE_ID_RE.match(spec.name):
        return f"model name {spec.name!r} must be a non-empty URL-safe identifier"
    if not spec.description:
        return f"{spec.name}: description (app blurb) is required"
    seen_params: set[str] = set()
    for param in spec.params:
        error = _validate_param(param)
        if error:
            return f"{spec.name}: {error}"
        if param.name in seen_params:
            return f"{spec.name}: duplicate param name {param.name!r}"
        seen_params.add(param.name)
    seen_ids: set[str] = set()
    for preset in spec.presets:
        error = _validate_preset(spec, preset)
        if error:
            return error
        if preset.id in seen_ids:
            return f"{spec.name}: duplicate preset id {preset.id!r}"
        seen_ids.add(preset.id)
    seen_mounts: set[str] = set()
    for mount in spec.mounts:
        if mount not in KNOWN_MOUNTS:
            return (
                f"{spec.name}: unknown mount type {mount!r} "
                f"(known: {sorted(KNOWN_MOUNTS)}) — add it to KNOWN_MOUNTS "
                "and give it a contract in tests/mount_contracts.py"
            )
        if mount in seen_mounts:
            return f"{spec.name}: duplicate mount type {mount!r}"
        seen_mounts.add(mount)
    orient = spec.print_orientation
    if (
        not isinstance(orient, tuple)
        or len(orient) != 3
        or not all(_is_number(c) and math.isfinite(c) for c in orient)
    ):
        return (
            f"{spec.name}: print_orientation must be a 3-tuple of finite "
            f"numbers, got {orient!r}"
        )
    if math.sqrt(sum(c * c for c in orient)) < 1e-9:
        return f"{spec.name}: print_orientation must be a non-zero vector"
    if not spec.is_smoke:
        if spec.category_id not in CATEGORY_IDS:
            return (
                f"{spec.name}: category_id {spec.category_id!r} must be one of "
                f"{sorted(CATEGORY_IDS)} (lib/models/catalog.ts)"
            )
        if not spec.presets:
            return (
                f"{spec.name}: app-listed models need at least one preset "
                "(--presets-only baking would skip it)"
            )
    return None


def register(spec: ModelSpec) -> ModelSpec:
    error = _validate_spec(spec)
    if error:
        raise ValueError(f"invalid model spec: {error}")
    if spec.name in _REGISTRY:
        raise ValueError(f"duplicate model name: {spec.name}")
    _REGISTRY[spec.name] = spec
    return spec


def all_models() -> list[ModelSpec]:
    # Import modules that register models (side-effect imports live here so
    # the harness has ONE place that defines "everything buildable").
    from holders import smoke  # noqa: F401  (toolchain smoke artifacts)
    try:
        from holders import cylindrical  # noqa: F401  (the PoC holder; lands via its bead)
    except ImportError:
        pass
    return list(_REGISTRY.values())
