"""Pinned Multiconnect short slots and continuous channels.

Local datum is the consumer back face (Y=0), with material at +Y.
Short slots receive heads from below along +Z. Continuous channels receive
heads through on-ramps along +Y, then the heads ride +Z as the consumer lowers.
Flush connector standoff is zero; no board/thread geometry is invented here.
"""
from inspect import signature
from math import isclose, isfinite
from build123d import Align, BuildPart, Locations, Pos, Rot, Part
from opengrid.multiconnect import Slot, SlotCutter, SnapInSlotCutter, RoundHeadCutter
from opengrid.multiconnect import SlotOpeningCutter
from .constants import PITCH

# Derived from the pinned cutter, including its axial clearances.
POCKET_DEPTH = RoundHeadCutter().bounding_box().size.Z
# A point pocket's on-ramp, as a channel's lowest: the opening clears Z=0.
POINT_ONRAMP = PITCH / 2


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


def channel_cutter(length: float, *, onramps, seats, drop: float = PITCH / 2) -> Part:
    """Continuous negative, spine Z=0..length, back face Y=0, pocket at +Y.

    Positions are explicit absolute Z centres. Heads enter along +Y at an
    on-ramp, then ride +Z by ``drop`` as the consumer lowers. Consumers must
    provide >=2.4 mm backing and a closed top; see the channel mount contract.
    Profiles and snap exclusions come exclusively from the pinned library.
    """
    if not isfinite(length) or length <= 0 or not isclose(length / PITCH, round(length / PITCH), rel_tol=0, abs_tol=1e-9):
        raise ValueError('length must be a positive multiple of 25 mm')
    return _spine(length, onramps, seats, drop)


def point_cutter(drop: float = PITCH / 2) -> Part:
    """One discrete pocket: a channel_cutter segment with one on-ramp and seat.

    Same frame and features as channel_cutter: on-ramp at Z=POINT_ONRAMP
    (a channel's lowest on-ramp), seat ``drop`` above it. The spine ends one
    library head-cutter radius above the seat, the shortest length that
    still clears the seated head. That is not a 25 mm multiple, which is why
    this is a separate entry point (pst-93yd5). Length: point_length(drop).
    """
    return _spine(point_length(drop), (POINT_ONRAMP,), (POINT_ONRAMP + drop,), drop)


def point_length(drop: float = PITCH / 2) -> float:
    return POINT_ONRAMP + drop + RoundHeadCutter().bounding_box().size.X / 2


def _spine(length, onramps, seats, drop) -> Part:
    if not isfinite(drop) or not 0 < drop < PITCH:
        raise ValueError('drop must be strictly between 0 and 25 mm')
    onramps, seats = tuple(onramps), tuple(seats)
    if any(not isfinite(z) for z in (*onramps, *seats)):
        raise ValueError('on-ramp and seat centres must be finite')
    if any(b - a < PITCH for a, b in zip(sorted(onramps), sorted(onramps)[1:])):
        raise ValueError('on-ramps must be at least 25 mm apart')
    if len(set(seats)) != len(seats):
        raise ValueError('seat centres must be unique')
    if any(sum(isclose(z, r + drop, rel_tol=0, abs_tol=1e-9) for r in onramps) != 1 for z in seats):
        raise ValueError('every seat must equal exactly one on-ramp + drop')

    transform = Pos(0, POCKET_DEPTH, 0) * Rot(90, 0, 0)
    opening = SlotOpeningCutter()
    # The difference isolates exactly the library's triangular snap exclusions,
    # including the paired seat heads that trim them. Unioning a snap slot into
    # a full spine would erase these features.
    notches = SlotCutter(align=(Align.CENTER, Align.MAX, Align.MIN)) - SnapInSlotCutter()
    for positions, feature in ((onramps, opening), (seats, notches)):
        bb = (transform * feature).bounding_box()
        if any(not 0 < z < length or z + bb.min.Z <= 0 or z + bb.max.Z >= length for z in positions):
            raise ValueError('full opening/notch must lie strictly inside the spine')

    class ChannelSlot(Slot):
        def __init__(self, **kwargs):
            kwargs['length'] = length
            super().__init__(**kwargs)

    # Compose in the native library frame before rotating once. Consumers
    # should place copies of this cutter for identical channels, as the demo
    # does, to preserve common curved-edge geometry for STL tessellation.
    cutter = SlotCutter(slot=ChannelSlot, align=(Align.CENTER, Align.MIN, Align.MIN))
    for z in seats:
        cutter -= Pos(0, z, 0) * notches
    for z in onramps:
        cutter += Pos(0, z, 0) * opening
    return transform * cutter
