"""Face-down rack plates: X across, Y from the panel bottom, Z rearwards."""
from math import isfinite
from build123d import Align, Box, Circle, Pos, RectangleRounded, Sketch, SlotOverall, chamfer, extrude
from . import constants as c


def panel_height(units):
    if isinstance(units, bool) or not isinstance(units, int) or not 1 <= units <= 7:
        raise ValueError('units must be an integer from 1 to 7')
    return units*c.RACK_UNIT-c.PANEL_SHORT


def hole_centres(units):
    panel_height(units)
    return [(x, u*c.RACK_UNIT+c.HOLE_EDGE+i*c.HOLE_PITCH-c.PANEL_SHORT/2)
            for x in (-c.HOLE_SPAN/2, c.HOLE_SPAN/2)
            for u in range(units) for i in range(c.HOLES_PER_UNIT)]


def ear_profile(units, slot_mm=0):
    """Negative sketch of the two ears' holes; slot_mm is overall length."""
    height = panel_height(units)
    if not isfinite(slot_mm) or slot_mm < 0 or slot_mm > c.MAX_SLOT_MM or 0 < slot_mm < c.EAR_HOLE_D:
        raise ValueError('ear ligament: slot_mm must be 0 (round) or 7..8 mm')
    length = slot_mm or c.EAR_HOLE_D
    profile = Sketch()
    for x, y in hole_centres(units):
        ligament = min(y-length/2, height-y-length/2, c.EAR_WIDTH/2-abs(x)-c.EAR_HOLE_D/2)
        if ligament < c.MIN_WALL_MM:
            raise ValueError(f'ear ligament {ligament:.3f} mm is below {c.MIN_WALL_MM} mm')
        hole = Circle(c.EAR_HOLE_D/2) if length == c.EAR_HOLE_D else SlotOverall(length, c.EAR_HOLE_D, rotation=90)
        profile += Pos(x, y)*hole
    return profile


def finish(part, functional=None):
    """45-degree relief on every sharp edge, including hole bed entrances."""
    adjacency = {}
    for face in part.faces():
        for edge in face.edges():
            adjacency.setdefault(edge, []).append(face)
    edges = []
    for edge, faces in adjacency.items():
        if len(faces) == 2 and not (functional and functional(edge)):
            normals = [f.normal_at(edge.center()) for f in faces]
            if normals[0].dot(normals[1]) < 0.99:
                edges.append(edge)
    return chamfer(edges, c.EDGE_CHAMFER) if edges else part


def panel(units, width_between_ears=None, *, slot_mm=0, finished=True):
    """Full-width plate, with 4 mm ear pads outside width_between_ears.

    The optional width is the central 3 mm region; hole centres and overall
    width remain the interface constants. Default pads start at the rack opening.
    """
    height = panel_height(units)
    width = c.CLEAR_OPENING if width_between_ears is None else width_between_ears
    if not isfinite(width) or not c.USABLE_WIDTH <= width <= c.CLEAR_OPENING:
        raise ValueError('width_between_ears must be between USABLE_WIDTH and CLEAR_OPENING')
    shape = Pos(0, height/2)*RectangleRounded(c.EAR_WIDTH, height, c.PANEL_CORNER)
    part = extrude(shape, amount=c.EAR_THICKNESS)
    part -= Pos(0, height/2, c.PANEL_THICKNESS)*Box(
        width, height+2, c.EAR_THICKNESS, align=(Align.CENTER, Align.CENTER, Align.MIN))
    part -= Pos(0, 0, -1)*extrude(ear_profile(units, slot_mm), amount=c.EAR_THICKNESS+2)
    return finish(part) if finished else part
