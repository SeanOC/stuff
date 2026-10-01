"""Independent compatibility geometry; no official tile/connector assets bundled."""
from .multiconnect import slot_cutter, channel_cutter
from . import fixpoint
from .pins import SmallHoleConePin


def LargeHoleThreadCutter(*args, **kwargs):
    raise NotImplementedError('No qualified male/female thread spec; docs/multibuild-research.md §2, §5')


# Fix Point (Regular) slot negative; namespaced so it never shadows the
# Multiconnect ``slot_cutter`` above (multibuild.fixpoint.slot_cutter).
FixPointCutter = fixpoint.slot_cutter
