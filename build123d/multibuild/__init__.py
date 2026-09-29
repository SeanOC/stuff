"""Independent compatibility geometry; no official tile/connector assets bundled."""
from .multiconnect import slot_cutter, channel_cutter
from .pins import SmallHoleConePin


def LargeHoleThreadCutter(*args, **kwargs):
    raise NotImplementedError('No qualified male/female thread spec; docs/multibuild-research.md §2, §5')


def FixPointCutter(*args, **kwargs):
    raise NotImplementedError('Multiconnect selected; Fix-Point deferred; docs/multibuild-research.md §3, §5')
