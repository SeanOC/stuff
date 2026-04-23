"""Invariants for the cartoonish popcorn kernel.

Seed set — built-ins (connected_solids == 1, watertight) cover the
structural claims. The sidecar exists so every model has one; extend
when a new defect class bites.
"""

from __future__ import annotations

from scripts.invariants import Failure, as_default_params


def check(ctx):
    failures = []
    p = as_default_params(ctx["params"])

    # base_cut shouldn't eat more than half the kernel height — past
    # that the "pop" silhouette reads as a flat chip.
    base_cut = p.get("base_cut")
    if base_cut is not None and base_cut > 8:
        failures.append(Failure(
            "silhouette",
            f"base_cut={base_cut}mm > 8mm; kernel will flatten into a chip shape",
        ))

    return failures
