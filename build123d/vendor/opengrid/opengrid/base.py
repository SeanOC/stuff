import math

from build123d import *
from mr import artifact
from mr import BuildEnv
from mr import customizable
from mr import Result
from pydantic import BaseModel
from pydantic import Field

from . import constants


class ConnectorCutter(BasePartObject):
    """Extruded connector pocket profile (XY sketch, +Z extrusion).

    Geometry from tangency: main R=2.6, side fillet 0.5, slot arc radius 5√5/4 mm,
    tiny bottom fillet 0.25; construction slot center (5.1, -2.5), sketch Y shifted so the
    bottom flat lies on Y=0 (slot center (5.1, 0) in the sketch).
    """

    def __init__(
        self,
        height: float = 2.4 * MM,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.extrusion_height = height

        r_main = 2.6 * MM
        r_fillet = 0.5 * MM
        r_tiny = 0.25 * MM
        slot_cx = 5.1 * MM
        slot_cy = -2.5 * MM
        r_slot = 5 * math.sqrt(5) / 4 * MM

        fillet_cx = r_main - r_fillet
        gap_x = slot_cx - fillet_cx
        fillet_cy = math.sqrt((r_slot + r_fillet) ** 2 - gap_x**2) + slot_cy

        tiny_cy = slot_cy + r_tiny
        tiny_cx = slot_cx - math.sqrt((r_slot - r_tiny) ** 2 - r_tiny**2)

        def _toward(
            ox: float, oy: float, r: float, tx: float, ty: float
        ) -> tuple[float, float]:
            dx, dy = tx - ox, ty - oy
            s = r / math.hypot(dx, dy)
            return (ox + dx * s, oy + dy * s)

        def _deg(cx: float, cy: float, px: float, py: float) -> float:
            return math.degrees(math.atan2(py - cy, px - cx))

        p_fillet_to_slot = _toward(slot_cx, slot_cy, r_slot, fillet_cx, fillet_cy)
        p_slot_to_tiny = _toward(slot_cx, slot_cy, r_slot, tiny_cx, tiny_cy)

        th_slot_start = _deg(slot_cx, slot_cy, *p_fillet_to_slot)
        th_slot_span = _deg(slot_cx, slot_cy, *p_slot_to_tiny) - th_slot_start

        th_corner_start = _deg(tiny_cx, tiny_cy, *p_slot_to_tiny)
        th_corner_span = 270.0 - th_corner_start

        # Shift profile in Y so the bottom flat (was y=slot_cy) lies on Y=0.
        dy = -slot_cy
        p_fs = (p_fillet_to_slot[0], p_fillet_to_slot[1] + dy)

        with BuildPart() as connector_cutter:
            with BuildSketch(Plane.XY):
                with BuildLine():
                    CenterArc((0, dy), r_main, start_angle=90, arc_size=-90)
                    Line((r_main, dy), (r_main, fillet_cy + dy))
                    TangentArc((r_main, fillet_cy + dy), p_fs, tangent=(0, -1))
                    CenterArc((slot_cx, 0), r_slot, th_slot_start, th_slot_span)
                    CenterArc(
                        (tiny_cx, tiny_cy + dy),
                        r_tiny,
                        th_corner_start,
                        th_corner_span,
                    )
                    Line((tiny_cx, 0), (0, 0))
                    mirror(about=Plane.YZ)
                make_face()
            extrude(amount=height / 2, both=True)

        super().__init__(
            connector_cutter.part, rotation=rotation, align=align, mode=mode
        )
        self.color = constants.NEGATIVE_MODEL_COLOR


class BaseSnapSlotCutter(BasePartObject):
    def __init__(
        self,
        open_grid_unit_size: float = constants.OPEN_GRID_UNIT_SIZE,
        open_grid_base_height: float = constants.OPEN_GRID_BASE_HEIGHT,
        snap_cut_bottom_width: float = 1.1 * MM,
        snap_cut_bottom_chamfer: float = 0.4 * MM,
        snap_cut_bottom_bump_height: float = 1 * MM,
        snap_cut_bottom_dent_height: float = 1 * MM,
        snap_cut_bottom_dent_width: float = 0.8 * MM,
        diagonal_snap_cut_corner_chamfer: float = 4.2 * MM,
        diagonal_snap_cut_offset_from_corner_chamfer: float = 2.6 * MM,
        diagonal_snap_cut_bump_chamfer: float = 1.4 * MM,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.open_grid_unit_size = open_grid_unit_size
        self.open_grid_base_height = open_grid_base_height
        self.snap_cut_bottom_width = snap_cut_bottom_width
        self.snap_cut_bottom_chamfer = snap_cut_bottom_chamfer
        self.snap_cut_bottom_bump_height = snap_cut_bottom_bump_height
        self.snap_cut_bottom_dent_height = snap_cut_bottom_dent_height
        self.snap_cut_bottom_dent_width = snap_cut_bottom_dent_width
        self.diagonal_snap_cut_corner_chamfer = diagonal_snap_cut_corner_chamfer
        self.diagonal_snap_cut_offset_from_corner_chamfer = (
            diagonal_snap_cut_offset_from_corner_chamfer
        )
        self.diagonal_snap_cut_bump_chamfer = diagonal_snap_cut_bump_chamfer

        half_open_grid_unit_size = self.open_grid_unit_size / 2
        half_open_grid_base_height = self.open_grid_base_height / 2

        with BuildPart() as snap_slot_tool:
            with BuildSketch(Plane.YZ):
                with BuildLine():
                    Polyline(
                        # 0
                        (-half_open_grid_unit_size, 0),
                        # 1
                        (-half_open_grid_unit_size + self.snap_cut_bottom_width, 0),
                        # 2
                        (
                            -half_open_grid_unit_size
                            + self.snap_cut_bottom_width
                            + self.snap_cut_bottom_chamfer,
                            self.snap_cut_bottom_chamfer,
                        ),
                        # 3
                        (
                            -half_open_grid_unit_size
                            + self.snap_cut_bottom_width
                            + self.snap_cut_bottom_chamfer,
                            self.snap_cut_bottom_chamfer
                            + self.snap_cut_bottom_bump_height,
                        ),
                        # 4
                        (
                            -half_open_grid_unit_size + self.snap_cut_bottom_dent_width,
                            half_open_grid_base_height
                            - self.snap_cut_bottom_dent_height,
                        ),
                        # 5
                        (
                            -half_open_grid_unit_size + self.snap_cut_bottom_dent_width,
                            half_open_grid_base_height,
                        ),
                        # 6
                        (-half_open_grid_unit_size, half_open_grid_base_height),
                        close=True,
                    )
                make_face()
            extrude(amount=half_open_grid_unit_size, both=True)
            mirror(about=Plane.XY.offset(half_open_grid_base_height))

        diagonal_width = (2 * (self.open_grid_unit_size**2)) ** 0.5
        half_diagonal_width = diagonal_width / 2
        diagonal_snap_cut_corner_offset = (
            2 * (self.diagonal_snap_cut_corner_chamfer**2)
        ) ** 0.5 / 2 + self.diagonal_snap_cut_offset_from_corner_chamfer

        with BuildPart() as diagonal_snap_slot_tool:
            with BuildSketch(Plane.XZ.rotated((0, 0, 45))) as ss:
                with BuildLine():
                    Polyline(
                        (-half_diagonal_width, 0),
                        (
                            -half_diagonal_width
                            + diagonal_snap_cut_corner_offset
                            - self.diagonal_snap_cut_bump_chamfer,
                            0,
                        ),
                        (
                            -half_diagonal_width + diagonal_snap_cut_corner_offset,
                            self.diagonal_snap_cut_bump_chamfer,
                        ),
                        (
                            -half_diagonal_width + diagonal_snap_cut_corner_offset,
                            half_open_grid_base_height,
                        ),
                        (-half_diagonal_width, half_open_grid_base_height),
                        close=True,
                    )
                make_face()
            extrude(amount=self.open_grid_unit_size, both=True)
            mirror(about=Plane.XY.offset(half_open_grid_base_height))

        slot_tool = snap_slot_tool.part
        with BuildPart() as cutter:
            Box(
                self.open_grid_unit_size,
                self.open_grid_unit_size,
                self.open_grid_base_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            with PolarLocations(0, 4, angular_range=360, rotate=True):
                add(slot_tool, mode=Mode.SUBTRACT)
                add(diagonal_snap_slot_tool, mode=Mode.SUBTRACT)
        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


class Base(BasePartObject):
    def __init__(
        self,
        open_grid_unit_size: float = constants.OPEN_GRID_UNIT_SIZE,
        open_grid_base_height: float = constants.OPEN_GRID_BASE_HEIGHT,
        x_count: int = 1,
        y_count: int = 1,
        snap_slot_cutter: type[BaseSnapSlotCutter] = BaseSnapSlotCutter,
        connector_cutter: type[ConnectorCutter] = ConnectorCutter,
        connector_cut_neg_y: bool = True,
        connector_cut_pos_y: bool = True,
        connector_cut_neg_x: bool = True,
        connector_cut_pos_x: bool = True,
        corner_chamfer: bool = True,
        corner_chamfer_length: float = 4.2 * MM,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if x_count < 1 or y_count < 1:
            raise ValueError("x_count and y_count must be >= 1")
        self.open_grid_unit_size = open_grid_unit_size
        self.open_grid_base_height = open_grid_base_height
        self.x_count = x_count
        self.y_count = y_count
        self.snap_slot_cutter = snap_slot_cutter
        self.connector_cutter = connector_cutter
        self.connector_cut_neg_y = connector_cut_neg_y
        self.connector_cut_pos_y = connector_cut_pos_y
        self.connector_cut_neg_x = connector_cut_neg_x
        self.connector_cut_pos_x = connector_cut_pos_x
        self.corner_chamfer = corner_chamfer
        self.corner_chamfer_length = corner_chamfer_length
        half_open_grid_base_height = self.open_grid_base_height / 2
        width = self.x_count * self.open_grid_unit_size
        depth = self.y_count * self.open_grid_unit_size
        # Outside BuildPart: avoid double-applying GridLocations (constructor + add()).
        slot_cutter = self.snap_slot_cutter()
        connector_cutter = None
        if self.connector_cutter is not None and (
            (
                self.x_count > 1
                and (self.connector_cut_neg_y or self.connector_cut_pos_y)
            )
            or (
                self.y_count > 1
                and (self.connector_cut_neg_x or self.connector_cut_pos_x)
            )
        ):
            connector_cutter = self.connector_cutter()
        with BuildPart() as base:
            Box(
                width,
                depth,
                self.open_grid_base_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            if self.corner_chamfer:
                chamfer(
                    base.part.edges().filter_by(Axis.Z),
                    length=self.corner_chamfer_length,
                )
            with GridLocations(
                self.open_grid_unit_size,
                self.open_grid_unit_size,
                self.x_count,
                self.y_count,
            ):
                add(slot_cutter, mode=Mode.SUBTRACT)
            if connector_cutter is not None:
                z = half_open_grid_base_height
                pitch = self.open_grid_unit_size
                if self.x_count > 1:
                    nx = self.x_count - 1
                    for edge_y, rot, enabled in (
                        (-depth / 2, (0, 0, 0), self.connector_cut_neg_y),
                        (depth / 2, (0, 0, 180), self.connector_cut_pos_y),
                    ):
                        if not enabled:
                            continue
                        with Locations((0, edge_y, z)):
                            with GridLocations(pitch, 0, nx, 1):
                                add(
                                    connector_cutter,
                                    mode=Mode.SUBTRACT,
                                    rotation=rot,
                                )
                if self.y_count > 1:
                    ny = self.y_count - 1
                    for edge_x, rot, enabled in (
                        (-width / 2, (0, 0, -90), self.connector_cut_neg_x),
                        (width / 2, (0, 0, 90), self.connector_cut_pos_x),
                    ):
                        if not enabled:
                            continue
                        with Locations((edge_x, 0, z)):
                            with GridLocations(0, pitch, 1, ny):
                                add(
                                    connector_cutter,
                                    mode=Mode.SUBTRACT,
                                    rotation=rot,
                                )
        super().__init__(base.part, rotation=rotation, align=align, mode=mode)


class OpenGridBaseParameters(BaseModel):
    """Knobs for the openGrid base plate generator."""

    x_count: int = Field(default=1, ge=1, description="Grid units along X")
    y_count: int = Field(default=1, ge=1, description="Grid units along Y")
    connector_cut_neg_y: bool = Field(
        default=True,
        description="Connector pockets along the -Y edge (between cells in X when x_count > 1)",
    )
    connector_cut_pos_y: bool = Field(
        default=True,
        description="Connector pockets along the +Y edge (between cells in X when x_count > 1)",
    )
    connector_cut_neg_x: bool = Field(
        default=True,
        description="Connector pockets along the -X edge (between cells in Y when y_count > 1)",
    )
    connector_cut_pos_x: bool = Field(
        default=True,
        description="Connector pockets along the +X edge (between cells in Y when y_count > 1)",
    )


@customizable(
    short_desc="openGrid base plate with configurable grid size",
    sample_parameters=OpenGridBaseParameters(x_count=2, y_count=3),
)
def custom_base(parameters: OpenGridBaseParameters):
    """Build an openGrid base with the requested cell counts along X and Y."""
    return Base(
        x_count=parameters.x_count,
        y_count=parameters.y_count,
        connector_cut_neg_y=parameters.connector_cut_neg_y,
        connector_cut_pos_y=parameters.connector_cut_pos_y,
        connector_cut_neg_x=parameters.connector_cut_neg_x,
        connector_cut_pos_x=parameters.connector_cut_pos_x,
    )


@artifact(
    sample=True,
    short_desc="Cutter (negative model) for an openGrid snap slot on the base",
)
def base_snap_slot_cutter():
    return BaseSnapSlotCutter()


def _with_version_mark(base: Base):
    build_env = BuildEnv.from_local_git_repo()
    if not build_env.versioned_model_enabled:
        return base
    with BuildPart() as versioned:
        add(base)
        version_mark = build_env.get_build_version()
        neg_y_face = versioned.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0]
        plane = Plane(neg_y_face)
        pitch = base.open_grid_unit_size
        depth = base.y_count * pitch
        # Cell 0 center X (GridLocations). On the -Y face this is the horizontal center of the
        # leftmost cell's band (between outer -X wall and the seam one pitch right), not the wall edge.
        left_cell_cx = (0 - (base.x_count - 1) / 2) * pitch
        mark_anchor = Vector(
            left_cell_cx,
            -depth / 2,
            base.open_grid_base_height / 2,
        )
        loc_2d = plane.to_local_coords(mark_anchor)
        with BuildSketch(neg_y_face):
            with Locations((loc_2d.X, loc_2d.Y)):
                Text(
                    version_mark,
                    font_size=constants.VERSION_MARK_FONT_SIZE,
                    rotation=-90,
                    align=(Align.CENTER, Align.CENTER),
                )
        extrude(amount=-constants.VERSION_MARK_DEPTH, mode=Mode.SUBTRACT)
    return Result(model=base, versioned=versioned)


@artifact(sample=True, short_desc="openGrid 1x1 Base")
def base_1x1():
    return _with_version_mark(Base())


@artifact(sample=True, short_desc="openGrid 2x3 Base", cover=True)
def base_2x3():
    return _with_version_mark(Base(x_count=2, y_count=3))


@artifact(sample=True, short_desc="Connector cutter (extruded pocket profile)")
def connector_cutter():
    return ConnectorCutter()
