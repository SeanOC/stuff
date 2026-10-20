"""OCCT operations whose public build123d equivalents change construction."""
from collections.abc import Sequence

from build123d import Edge, Face, Part
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer


class AngledChamferInvalid(Exception):
    """An OCCT result failed validation; retain the selected edges for diagnosis.

    Deliberately not ValueError: callers must opt into a fallback for invalid
    chamfers, rather than swallowing them in a general ValueError handler.
    """

    def __init__(self, edges: Sequence[Edge]):
        self.edges = list(edges)
        super().__init__(f"angled chamfer produced invalid geometry: {self.edges!r}")


def angled_chamfer(
    part: Part, edge_faces: Sequence[tuple[Edge, Face]], distance: float, angle: float
) -> Part:
    """Chamfer all edge/reference-face pairs in ONE builder; angle is radians.

    AddDA pins the angle to each reference face. Public build123d chamfer
    converts its angle to two distances, which is not equivalent on oblique
    curved walls. Pass the caller's angle through unchanged:

    * Container uses 45.01 degrees for the overhang-gate margin; its straight
      default loop also passes at 45.0.
    * Gridfinity shelf uses 45.01: OCCT's fitted curved bevels can overshoot
      nominal by ~0.0012 degrees, beyond the audit's 45 + 0.001 degree limit.
    * Cup lid uses exactly pi/4 to pin the angle on its oblique curved wall.
    * Drawer shell skips existing 45-degree magnet cones (re-chamfering them
      is degenerate), then cuts the cones separately. At maximum clearance,
      opposing 0.3 mm bevels collapse a 0.6 mm strip; its section-sweep
      fallback handles StdFail_NotDone, independently of the angle margin.

    Wrap with public Part, without ShapeFix or cleanup. StdFail_NotDone
    propagates to the caller; only a returned, invalid shape raises
    AngledChamferInvalid. Cleanup and fallback choices belong to the caller.
    """
    builder = BRepFilletAPI_MakeChamfer(part.wrapped)
    for edge, face in edge_faces:
        builder.AddDA(distance, angle, edge.wrapped, face.wrapped)
    result = Part(builder.Shape())
    if not result.is_valid:
        raise AngledChamferInvalid([edge for edge, _ in edge_faces])
    return result
