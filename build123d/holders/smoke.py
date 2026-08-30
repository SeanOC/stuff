"""Toolchain smoke artifacts — library-provided parts, prove the pipeline."""
from opengrid.base import Base
from opengrid.multiconnect import RoundHead

from holders.registry import ModelSpec, register

register(ModelSpec(
    name="smoke_opengrid_tile_1x1",
    build=lambda: Base(),
    description="openGrid 1x1 tile straight from the opengrid library",
    tags=("smoke",),
))
register(ModelSpec(
    name="smoke_multiconnect_roundhead",
    build=lambda: RoundHead(),
    description="Multiconnect male round head straight from the opengrid library",
    tags=("smoke",),
))
