"""Invariants for the vendored Disney ear hanger (st-w2g).

This is an externally-authored model imported from MakerWorld with the
original `.scad` body intact. We don't claim authorship, so there are
no original geometric invariants to assert beyond the built-ins
(watertight, orphan-fragment, triangle ceiling). Pin topology so a
future regression — e.g. an accidental `difference()` that severs the
hanger from its tab — surfaces loudly.
"""

from __future__ import annotations

from scripts.invariants import Failure, expect_connected_solids


def check(ctx):
    return list(expect_connected_solids(ctx, 1))
