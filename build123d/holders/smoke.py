"""Toolchain smoke artifacts — library-provided parts, prove the pipeline.

Smoke models are registered (the harness builds + tests them) but are
EXCLUDED from the app-facing manifest and --presets-only baking: they are
pipeline canaries, not app-listed models.
"""
from opengrid.base import Base
from opengrid.multiconnect import RoundHead

from holders.registry import ModelSpec, register

register(ModelSpec(
    name="smoke_opengrid_tile_1x1",
    build=lambda values: Base(),
    description="openGrid 1x1 tile straight from the opengrid library",
    tags=("smoke",),
))
register(ModelSpec(
    name="smoke_multiconnect_roundhead",
    build=lambda values: RoundHead(),
    description="Multiconnect male round head straight from the opengrid library",
    tags=("smoke",),
))
