"""Pinned Multiconnect negatives with 25 mm travel increments.

Local datum is the consumer back face (Y=0), with material at +Y.
Lower the consumer onto the head: head entry is +Z, above the open end.
Flush connector standoff is zero; no board/thread geometry is invented here.
"""
from inspect import signature
from math import isclose, isfinite
from build123d import Align, BuildPart, Locations, Pos, Rot, Part
from opengrid.multiconnect import Slot, SlotCutter, SnapInSlotCutter, RoundHeadCutter
from .constants import PITCH

# Derived from the pinned cutter, including its axial clearances.
POCKET_DEPTH = RoundHeadCutter().bounding_box().size.Z


def slot_cutter(travel: float = PITCH, *, snap: bool = False) -> Part:
    if not isfinite(travel) or travel <= 0 or not isclose(travel / PITCH, round(travel / PITCH), rel_tol=0, abs_tol=1e-9):
        raise ValueError('travel must be a positive multiple of 25 mm')

    class TravelSlot(Slot):
        def __init__(self, **kwargs):
            kwargs['length'] = travel
            super().__init__(**kwargs)

    class TravelCutter(SlotCutter):
        def __init__(self, **kwargs):
            kwargs['slot'] = TravelSlot
            super().__init__(**kwargs)

    if snap:
        cutter = SnapInSlotCutter(slot_cutter=TravelCutter)
    else:
        # Library snap assembly without detent triangles; retain both seat heads.
        spacing = signature(SnapInSlotCutter).parameters['head_spacing'].default
        with BuildPart() as assembly:
            TravelCutter(align=(Align.CENTER, Align.MAX, Align.MIN))
            with Locations((0, 0, 0), (0, -spacing, 0)):
                RoundHeadCutter()
        cutter = assembly.part
    return Pos(0, POCKET_DEPTH, 0) * Rot(90, 0, 0) * cutter
