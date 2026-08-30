"""Model registry — the contract between models and the export/test harness.

Register every buildable artifact here. The export harness (scripts/export.py)
and the test suite (tests/) iterate this registry, so a new model gets STL+GLB
+PNG export and mesh sanity tests for free by registering itself.
"""
from dataclasses import dataclass, field
from typing import Callable

from build123d import Part


@dataclass(frozen=True)
class ModelSpec:
    name: str                      # artifact basename, e.g. "holder_spray_can"
    build: Callable[[], Part]      # returns the finished Part
    description: str = ""
    tags: tuple[str, ...] = ()


_REGISTRY: dict[str, ModelSpec] = {}


def register(spec: ModelSpec) -> ModelSpec:
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
