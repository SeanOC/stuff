from build123d import *
from mr import artifact
from mr import BuildEnv
from mr import Result

from . import constants


class Slot(BasePartObject):
    """Multiconnect slot derived from the RoundHead side silhouette.

    The slot is the `RoundHead` profile projected onto the `XZ` panel and then
    extruded along `Y` for one openGrid unit. It is commonly paired with
    `RoundHead` to form an attachment point with a larger engagement surface.
    """

    def __init__(
        self,
        length: float = constants.MULTICONNECT_SLOT_LENGTH,
        bottom_width: float = constants.MULTICONNECT_SLOT_BOTTOM_WIDTH,
        top_width: float = constants.MULTICONNECT_SLOT_TOP_WIDTH,
        bottom_height: float = constants.MULTICONNECT_SLOT_BOTTOM_HEIGHT,
        taper_height: float = constants.MULTICONNECT_SLOT_TAPER_HEIGHT,
        top_height: float = constants.MULTICONNECT_SLOT_TOP_HEIGHT,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if length <= 0 or bottom_width <= 0 or top_width <= 0:
            raise ValueError("length, bottom_width, and top_width must be > 0")
        if bottom_height <= 0 or taper_height <= 0 or top_height <= 0:
            raise ValueError("all heights must be > 0")
        if bottom_width < top_width:
            raise ValueError("bottom_width must be >= top_width")

        z0 = 0.0
        z1 = bottom_height
        z2 = bottom_height + taper_height
        z3 = z2 + top_height
        half_bottom_width = bottom_width / 2
        half_top_width = top_width / 2

        with BuildPart() as part:
            # Side projection of RoundHead on XZ, then extruded along Y.
            with BuildSketch(Plane.XZ):
                with BuildLine():
                    Polyline(
                        (0, z0),
                        (half_bottom_width, z0),
                        (half_bottom_width, z1),
                        (half_top_width, z2),
                        (half_top_width, z3),
                        (0, z3),
                    )
                    mirror(about=Plane.YZ)
                make_face()
            extrude(amount=length / 2, both=True)

        super().__init__(part.part, rotation=rotation, align=align, mode=mode)


class RoundHead(BasePartObject):
    """Round head for multiconnect retention and snap engagement.

    This is the mating head shape that another component's snap slot
    latches onto in openGrid-style assemblies (often paired with a screw).
    """

    def __init__(
        self,
        bottom_radius: float = constants.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS,
        bottom_height: float = constants.MULTICONNECT_ROUND_HEAD_BOTTOM_HEIGHT,
        top_radius: float = constants.MULTICONNECT_ROUND_HEAD_TOP_RADIUS,
        taper_height: float = constants.MULTICONNECT_ROUND_HEAD_TAPER_HEIGHT,
        top_height: float = constants.MULTICONNECT_ROUND_HEAD_TOP_HEIGHT,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if bottom_radius <= 0:
            raise ValueError("bottom_radius must be > 0")
        if top_radius <= 0:
            raise ValueError("top_radius must be > 0")
        if bottom_height <= 0 or taper_height <= 0 or top_height <= 0:
            raise ValueError("all heights must be > 0")

        with BuildPart() as part:
            # Bottom pad.
            Cylinder(
                radius=bottom_radius,
                height=bottom_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            # Tapered transition from bottom radius to top radius.
            with BuildSketch(Plane.XY.offset(bottom_height)):
                Circle(bottom_radius)
            with BuildSketch(Plane.XY.offset(bottom_height + taper_height)):
                Circle(top_radius)
            loft(mode=Mode.ADD)
            # Top pad.
            with Locations((0, 0, bottom_height + taper_height)):
                Cylinder(
                    radius=top_radius,
                    height=top_height,
                    align=(Align.CENTER, Align.CENTER, Align.MIN),
                )

        super().__init__(part.part, rotation=rotation, align=align, mode=mode)


class SnapInSlot(BasePartObject):
    """Slot and round head with major side notches."""

    def __init__(
        self,
        slot: type[Slot] = Slot,
        round_head: type[RoundHead] = RoundHead,
        *,
        side_notch_length: float = constants.MULTICONNECT_SLOT_LENGTH,
        side_notch_bottom_width: float = constants.MULTICONNECT_SLOT_BOTTOM_WIDTH,
        side_notch_length_reference: float = constants.OPEN_GRID_UNIT_SIZE,
        side_notch_bottom_height: float = constants.MULTICONNECT_SLOT_BOTTOM_HEIGHT,
        side_notch_taper_height: float = constants.MULTICONNECT_SLOT_TAPER_HEIGHT,
        side_notch_top_height: float = constants.MULTICONNECT_SLOT_TOP_HEIGHT,
        side_notch_extrude_margin: float = 0.5 * MM,
        side_notch_axis_outset: float = 3.041 * MM,
        side_notch_radius: float = 3.675 * MM,
        # Intentional asymmetry (matches reference multiconnect): 3.494 mm from top on X- vs 6.494 mm
        # on X+. Same Y on both sides lets the printed part slide; a small offset improves stick.
        side_notch_major_y_from_top_neg_x: float = 3.494 * MM,
        side_notch_major_y_from_top_pos_x: float = 6.494 * MM,
        side_notch_edge_fillet_radius: float = 2.0 * MM,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.slot = slot
        self.round_head = round_head
        self.side_notch_length = side_notch_length
        self.side_notch_bottom_width = side_notch_bottom_width
        self.side_notch_length_reference = side_notch_length_reference
        self.side_notch_bottom_height = side_notch_bottom_height
        self.side_notch_taper_height = side_notch_taper_height
        self.side_notch_top_height = side_notch_top_height
        self.side_notch_extrude_margin = side_notch_extrude_margin
        self.side_notch_axis_outset = side_notch_axis_outset
        self.side_notch_radius = side_notch_radius
        self.side_notch_major_y_from_top_neg_x = side_notch_major_y_from_top_neg_x
        self.side_notch_major_y_from_top_pos_x = side_notch_major_y_from_top_pos_x
        self.side_notch_edge_fillet_radius = side_notch_edge_fillet_radius
        half_w = self.side_notch_bottom_width / 2
        scale = self.side_notch_length / self.side_notch_length_reference
        notch_hz = (
            self.side_notch_bottom_height
            + self.side_notch_taper_height
            + self.side_notch_top_height
            + self.side_notch_extrude_margin
        )
        y_neg_x = -(self.side_notch_major_y_from_top_neg_x * scale)
        y_pos_x = -(self.side_notch_major_y_from_top_pos_x * scale)
        majors = (
            (-half_w - self.side_notch_axis_outset, y_neg_x),
            (half_w + self.side_notch_axis_outset, y_pos_x),
        )

        with BuildPart() as part:
            self.round_head()
            self.slot(align=(Align.CENTER, Align.MAX, Align.MIN))
            # One sketch + one extrude with Locations() merges both cuts; OCCT then does not
            # give two independent Z seams per notch, so Select.LAST + fillet breaks.
            for cx, cy in majors:
                with BuildSketch(Plane.XY) as _:
                    with BuildLine():
                        CenterArc(
                            (cx, cy),
                            self.side_notch_radius,
                            start_angle=0,
                            arc_size=360,
                        )
                    make_face()
                extrude(amount=notch_hz, mode=Mode.SUBTRACT)
                notch_edges = part.edges(Select.LAST).filter_by(Axis.Z)
                fillet(notch_edges, self.side_notch_edge_fillet_radius)

        super().__init__(part.part, rotation=rotation, align=align, mode=mode)


class RoundHeadCutter(BasePartObject):
    def __init__(
        self,
        bottom_radius_clearance: float = 0.15 * MM,
        bottom_height_clearance: float = 0.212132034 * MM,
        top_radius_clearance: float = 0.15 * MM,
        top_height_clearance: float = -0.062132034 * MM,
        round_head: type[RoundHead] = RoundHead,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.round_head = round_head

        with BuildPart() as cutter:
            self.round_head(
                bottom_radius=(
                    constants.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS
                    + bottom_radius_clearance
                ),
                bottom_height=(
                    constants.MULTICONNECT_ROUND_HEAD_BOTTOM_HEIGHT
                    + bottom_height_clearance
                ),
                top_radius=(
                    constants.MULTICONNECT_ROUND_HEAD_TOP_RADIUS + top_radius_clearance
                ),
                taper_height=constants.MULTICONNECT_ROUND_HEAD_TAPER_HEIGHT,
                top_height=(
                    constants.MULTICONNECT_ROUND_HEAD_TOP_HEIGHT + top_height_clearance
                ),
            )

        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


class SlotCutter(BasePartObject):
    """Negative cutter for `Slot` with fit clearances."""

    def __init__(
        self,
        bottom_width_clearance: float = 0.3 * MM,
        bottom_height_clearance: float = 0.212132034 * MM,
        top_width_clearance: float = 0.3 * MM,
        top_height_clearance: float = -0.062132034 * MM,
        slot: type[Slot] = Slot,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.slot = slot

        with BuildPart() as cutter:
            self.slot(
                length=constants.MULTICONNECT_SLOT_LENGTH,
                bottom_width=(
                    constants.MULTICONNECT_SLOT_BOTTOM_WIDTH + bottom_width_clearance
                ),
                top_width=constants.MULTICONNECT_SLOT_TOP_WIDTH + top_width_clearance,
                bottom_height=(
                    constants.MULTICONNECT_SLOT_BOTTOM_HEIGHT + bottom_height_clearance
                ),
                taper_height=constants.MULTICONNECT_SLOT_TAPER_HEIGHT,
                top_height=constants.MULTICONNECT_SLOT_TOP_HEIGHT
                + top_height_clearance,
            )

        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


class SnapInSlotCutter(BasePartObject):
    """Negative cutter for a snap-in slot pocket."""

    def __init__(
        self,
        head_spacing: float = 0.795 * MM,
        slot_side_triangle_y_offset: float = 0.795 * MM,
        slot_side_triangle_base: float = 8 * MM,
        slot_side_triangle_inset: float = 0.6 * MM,
        bottom_width_clearance: float = 0.3 * MM,
        top_height_clearance: float = -0.062132034 * MM,
        round_head_cutter: type[RoundHeadCutter] = RoundHeadCutter,
        slot_cutter: type[SlotCutter] = SlotCutter,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.round_head_cutter = round_head_cutter
        self.slot_cutter = slot_cutter
        self.head_spacing = head_spacing
        self.slot_side_triangle_y_offset = slot_side_triangle_y_offset
        self.slot_side_triangle_base = slot_side_triangle_base
        self.slot_side_triangle_inset = slot_side_triangle_inset
        self.bottom_width_clearance = bottom_width_clearance
        self.top_height_clearance = top_height_clearance

        bw = constants.MULTICONNECT_SLOT_BOTTOM_WIDTH + self.bottom_width_clearance
        half_bw = bw / 2
        if self.slot_side_triangle_inset >= half_bw:
            raise ValueError("slot_side_triangle_inset must be < half bottom width")
        if self.slot_side_triangle_base <= 0 or self.slot_side_triangle_inset <= 0:
            raise ValueError("triangle base and inset must be > 0")

        with BuildPart() as cutter:
            self.slot_cutter(
                bottom_width_clearance=self.bottom_width_clearance,
                top_height_clearance=self.top_height_clearance,
                align=(Align.CENTER, Align.MAX, Align.MIN),
            )

            with BuildSketch(Plane.XY, mode=Mode.PRIVATE):
                with BuildLine():
                    Polyline(
                        (
                            half_bw - self.slot_side_triangle_inset,
                            -self.slot_side_triangle_y_offset,
                        ),
                        (half_bw, -self.slot_side_triangle_y_offset),
                        (
                            half_bw,
                            -self.slot_side_triangle_y_offset
                            - self.slot_side_triangle_base,
                        ),
                        close=True,
                    )
                tri_sk = make_face()
            face_pos_x = tri_sk.faces()[0]
            extrude(
                [face_pos_x, face_pos_x.mirror(Plane.YZ)],
                until=Until.LAST,
                dir=(0, 0, 1),
                mode=Mode.SUBTRACT,
            )

            with Locations((0, 0, 0), (0, -self.head_spacing, 0)):
                self.round_head_cutter()

        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


class SlotOpeningCutter(BasePartObject):
    """Negative cutter for the opening that lets a `RoundHead` insert along +Z.

    This is the conical frustum subtracted from a panel so the round head can be
    pushed in vertically; it is not the full slot profile (`SlotCutter`).
    """

    def __init__(
        self,
        bottom_radius_clearance: float = 0.15 * MM,
        top_radius_clearance: float = 1 * MM,
        height_clearance: float = 0 * MM,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        base = constants.MULTICONNECT_ROUND_HEAD_BOTTOM_RADIUS
        bottom_radius = base + bottom_radius_clearance
        top_radius = base + top_radius_clearance
        height = constants.MULTICONNECT_SLOT_OPENING_HEIGHT + height_clearance
        if bottom_radius <= 0 or top_radius <= 0:
            raise ValueError("bottom_radius and top_radius must be > 0")
        if height <= 0:
            raise ValueError("height must be > 0")

        with BuildPart() as cutter:
            with BuildSketch(Plane.XY):
                Circle(bottom_radius)
            with BuildSketch(Plane.XY.offset(height)):
                Circle(top_radius)
            loft(mode=Mode.ADD)

        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


class SnapInQuickConnectTopBackCutter(BasePartObject):
    """Negative cutter: snap-in slot pocket plus vertical round-head opening."""

    def __init__(
        self,
        open_grid_unit_size: float = constants.OPEN_GRID_UNIT_SIZE,
        snap_in_slot_cutter: type[SnapInSlotCutter] = SnapInSlotCutter,
        slot_opening_cutter: type[SlotOpeningCutter] = SlotOpeningCutter,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        self.open_grid_unit_size = open_grid_unit_size
        self.snap_in_slot_cutter = snap_in_slot_cutter
        self.slot_opening_cutter = slot_opening_cutter

        with BuildPart() as cutter:
            self.snap_in_slot_cutter()
            with Locations((0, -self.open_grid_unit_size / 2, 0)):
                self.slot_opening_cutter()
            Box(
                self.open_grid_unit_size,
                self.open_grid_unit_size,
                self.open_grid_unit_size,
                mode=Mode.INTERSECT,
            )

        super().__init__(cutter.part, rotation=rotation, align=align, mode=mode)
        self.color = constants.NEGATIVE_MODEL_COLOR


@artifact(sample=True, short_desc="Round head for multiconnect snap engagement")
def round_head():
    """Default round head for multiconnect retention and snap engagement.

    This artifact provides the mating head shape that another component's
    snap slot latches onto in openGrid-style assemblies.
    """
    return RoundHead()


@artifact(sample=True, short_desc="Multiconnect slot body")
def slot():
    """Multiconnect slot from the RoundHead side profile projection."""
    return Slot()


@artifact(
    sample=True,
    short_desc="Slot fused with round head for more contact area (snap-in tab)",
)
def snap_in_slot():
    """Slot and round head in one body—typically for a larger mating surface in multiconnect snaps."""
    return SnapInSlot()


@artifact(sample=True, short_desc="Negative cutter for slot with clearance")
def slot_cutter():
    """Default negative cutter for the multiconnect slot interface."""
    return SlotCutter()


@artifact(sample=True, short_desc="Negative cutter for round head with clearance")
def round_head_cutter():
    """Default negative cutter for the multiconnect round-head interface."""
    return RoundHeadCutter()


@artifact(
    sample=True,
    short_desc="Cutter opening for vertical RoundHead insertion",
)
def slot_opening_cutter():
    """Negative cutter for the through-opening sized for vertical RoundHead entry."""
    return SlotOpeningCutter()


@artifact(
    sample=True,
    short_desc="Negative cutter for snap-in slot pocket",
)
def snap_in_slot_cutter():
    """Negative cutter for a snap-in slot pocket."""
    return SnapInSlotCutter()


@artifact(
    sample=True,
    short_desc="Snap-in slot pocket + slot opening (quick-connect top/back)",
)
def snap_in_quick_connect_top_back_cutter():
    """Combined negative of `SnapInSlotCutter` and `SlotOpeningCutter` for top/back quick-connect."""
    return SnapInQuickConnectTopBackCutter()


@artifact(
    sample=True,
    short_desc="Snap-in slot cutter fitting test",
)
def snap_in_slot_cutter_fitting_test():
    plate_height = 6.4 * MM
    box = Box(
        constants.OPEN_GRID_UNIT_SIZE,
        constants.OPEN_GRID_UNIT_SIZE * 1.5,
        plate_height,
        align=(Align.CENTER, Align.MAX, Align.MIN),
    )
    box -= SnapInSlotCutter(
        rotation=(180, 0, 0),
        align=(Align.CENTER, Align.MIN, Align.MAX),
        mode=Mode.SUBTRACT,
    )
    build_env = BuildEnv.from_local_git_repo()
    if not build_env.versioned_model_enabled:
        return box
    with BuildPart() as versioned:
        add(box)
        version_mark = build_env.get_build_version()
        neg_y_face = versioned.faces().filter_by(Axis.Y).sort_by(Axis.Y)[0]
        plane = Plane(neg_y_face)
        mark_anchor = neg_y_face.center()
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
    return Result(model=box, versioned=versioned)
