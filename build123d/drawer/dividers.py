# SPDX-License-Identifier: CC-BY-SA-4.0
"""Compartment lists shared by the shell and container dividers.

[C] assets/openConnect-drawer/openconnect_drawer_online.scad:399-417 and
:1586-1589. A list is comma-separated whole numbers of grid units. Running
sums below the grid count become divider positions. The remainder becomes
the last compartment, so the author's "3,3" on a 5-tile shell gives
compartments [3, 2], and a list whose first entry already reaches the count
gives no divider. The author's parser turns spaces into empty entries; the
port removes spaces instead.
"""
from dataclasses import dataclass
import re

ENTRY = re.compile(r'[0-9]+')


class CompartmentListError(ValueError):
    """A compartment list or grid count the author's parser cannot use."""


@dataclass(frozen=True)
class Compartments:
    count: int
    positions: tuple  # running sums < count: one divider each
    sizes: tuple      # compartment sizes, summing to count


def parse(text, count, name):
    """Parse ``text`` for a grid of ``count`` units; ``name`` labels errors."""
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise CompartmentListError(f'{name}: grid count must be a whole number of at least 1')
    entries = str(text).replace(' ', '').strip(',').split(',')
    if entries == ['']:
        raise CompartmentListError(f'{name}: compartment list is empty')
    sizes = []
    for entry in entries:
        if not ENTRY.fullmatch(entry) or int(entry) < 1:
            raise CompartmentListError(
                f'{name}: compartment {entry!r} is not a positive whole number')
        sizes.append(int(entry))
    positions, total = [], 0
    for size in sizes:
        total += size
        if total >= count:
            break
        positions.append(total)
    kept = sizes[:len(positions)]
    return Compartments(count, tuple(positions),
                        tuple(kept + [count - (positions[-1] if positions else 0)]))
