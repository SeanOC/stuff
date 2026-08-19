"""Invariants for the Disney ear hanger (remix, pst-15du).

Derivative of an externally-authored MakerWorld model (CC BY-NC-SA
4.0) with the original `.scad` body intact — house-style @param /
anchor wiring only, geometry identical at defaults. We don't claim
authorship, so there are no original geometric invariants beyond the
built-ins (watertight, orphan-fragment, triangle ceiling, and the
PRINT_ANCHOR_BBOX drift check now that the model declares an anchor).
Pin topology so a future regression — e.g. an accidental
`difference()` that severs the hanger from its tab — surfaces loudly.
"""

from __future__ import annotations

from scripts.invariants import Failure, expect_connected_solids


def check(ctx):
    return list(expect_connected_solids(ctx, 1))
