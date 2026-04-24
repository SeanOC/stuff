"""Invariants for the Aquor bib drip deflector (st-2ln rewrite).

The part is a bent plate — horizontal VHB tab + angled flap. Two
claims worth pinning beyond the built-ins:

1. **Single-body.** The tab and flap union should produce one solid.
   A non-overlapping hinge would surface as two orphan components,
   which the orphan-fragment built-in would catch only if one of
   them were tiny — this nails the topology explicitly.

2. **Volume ceiling.** This is a thin-plate geometry; if a future
   edit regresses to a solid-block interpretation (st-s7b shipped
   ~44 cm³), the volume check flags it loudly. 15 cm³ is the soft
   warn line per the bead; 30 cm³ is a hard fail ("something is
   very wrong, this isn't a bent plate anymore").
"""

from __future__ import annotations

from scripts.invariants import Failure, expect_connected_solids


# Upper bounds on the part volume. The bent-plate geometry lives at
# ~7–8 cm³ at defaults; doubling-and-some room leaves slack for a
# user who cranks flap_length to 60 or flap_thickness to 5.
_VOLUME_WARN_MM3 = 15_000
_VOLUME_FAIL_MM3 = 30_000


def check(ctx):
    failures = list(expect_connected_solids(ctx, 1))

    mesh = ctx["stl"]
    volume = float(mesh.volume)
    if volume > _VOLUME_FAIL_MM3:
        failures.append(Failure(
            "geometry",
            f"STL volume {volume:.0f}mm³ exceeds {_VOLUME_FAIL_MM3}mm³ — "
            "the part is supposed to be a bent plate (≤ ~15 cm³), not a "
            "solid block. Check that st-2ln's bent-plate rewrite hasn't "
            "regressed to a scoop/wedge.",
        ))
    elif volume > _VOLUME_WARN_MM3:
        failures.append(Failure(
            "geometry",
            f"STL volume {volume:.0f}mm³ exceeds the {_VOLUME_WARN_MM3}mm³ "
            "warn threshold for this model — verify the geometry is still "
            "a bent plate (tab + flap), not a scoop/wedge.",
        ))

    return failures
