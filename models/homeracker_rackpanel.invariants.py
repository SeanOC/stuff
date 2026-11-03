"""HomeRacker rackpanel: one watertight default, upstream envelope and volume.

Every preset is also compared to the pinned upstream reference in the wasm
sweep. Frame dimensions and tolerances must not drift when libraries change.
"""
from scripts.invariants import Failure, expect_connected_solids


def check(ctx):
    failures = expect_connected_solids(ctx, 1)
    expected = [254.0, 44.45, 2.0]
    if any(abs(got - want) > 0.01 for got, want in zip(ctx["bbox_mm"], expected)):
        failures.append(Failure("envelope", f"Expected {expected}, got {ctx['bbox_mm']}"))
    reference_volume = 21836.193388
    if abs(ctx["stl"].volume / reference_volume - 1) > 0.001:
        failures.append(Failure("volume", "Default differs from pinned upstream by >0.1%"))
    if abs(ctx["stl"].bounds[0, 2]) > 0.01:
        failures.append(Failure("print-plane", "Default must rest on Z=0"))
    return failures
