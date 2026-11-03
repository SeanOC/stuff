from build123d import *
from mr import artifact
from mr import BuildEnv
from mr import Result

from . import constants
from .multiconnect import SnapInSlotCutter


class ZipTieModule(BasePartObject):
    """Unit-size module that snaps onto a RoundHead and retains a zip tie.

    One face is cut with `SnapInSlotCutter` for multiconnect snap engagement.
    The opposite face has a rectangular pocket with a centered bridge spanning
    the pocket's long sides so a zip tie can pass under the bridge. The bridge
    has a trapezoid profile so its entry faces slope and guide the zip tie in;
    additional top-face entry ramps run down to the slot floor so a tip can
    slide in and back out, with a light fillet where each ramp meets the floor.
    Outer corners, top edges, and the bridge underside are lightly filleted.
    """

    def __init__(
        self,
        open_grid_unit_size: float = constants.OPEN_GRID_UNIT_SIZE,
        module_height: float = 9.5 * MM,
        zip_tie_slot_length: float = 18 * MM,
        zip_tie_slot_width: float = 16 * MM,
        zip_tie_slot_depth: float = 4 * MM,
        bridge_top_width: float = 10 * MM,
        bridge_bottom_width: float = 4.5 * MM,
        bridge_thickness: float = 2 * MM,
        entry_slope_run: float = 2.5 * MM,
        outer_fillet_radius: float = 1.5 * MM,
        top_fillet_radius: float = 0.6 * MM,
        bridge_fillet_radius: float = 0.5 * MM,
        slope_floor_fillet_radius: float = 0.8 * MM,
        snap_in_slot_cutter: type[SnapInSlotCutter] = SnapInSlotCutter,
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] | None = None,
        mode: Mode = Mode.ADD,
    ):
        if open_grid_unit_size <= 0 or module_height <= 0:
            raise ValueError("open_grid_unit_size and module_height must be > 0")
        if zip_tie_slot_length <= 0 or zip_tie_slot_width <= 0:
            raise ValueError("zip_tie_slot_length and zip_tie_slot_width must be > 0")
        if zip_tie_slot_depth <= 0 or bridge_thickness <= 0:
            raise ValueError("slot depth and bridge_thickness must be > 0")
        if bridge_top_width <= 0 or bridge_bottom_width <= 0:
            raise ValueError("bridge widths must be > 0")
        if bridge_bottom_width > bridge_top_width:
            raise ValueError("bridge_bottom_width must be <= bridge_top_width")
        if bridge_thickness >= zip_tie_slot_depth:
            raise ValueError("bridge_thickness must be < zip_tie_slot_depth")
        if bridge_top_width >= zip_tie_slot_width:
            raise ValueError("bridge_top_width must be < zip_tie_slot_width")
        if entry_slope_run < 0:
            raise ValueError("entry_slope_run must be >= 0")
        if outer_fillet_radius < 0 or top_fillet_radius < 0 or bridge_fillet_radius < 0:
            raise ValueError("fillet radii must be >= 0")
        if slope_floor_fillet_radius < 0:
            raise ValueError("slope_floor_fillet_radius must be >= 0")
        half_outer = open_grid_unit_size / 2
        half_slot_width = zip_tie_slot_width / 2
        if half_slot_width + entry_slope_run >= half_outer:
            raise ValueError("slot width + entry_slope_run must fit in the unit")
        if zip_tie_slot_length >= open_grid_unit_size:
            raise ValueError("zip_tie_slot_length must be < open_grid_unit_size")
        if zip_tie_slot_width >= open_grid_unit_size:
            raise ValueError("zip_tie_slot_width must be < open_grid_unit_size")

        self.open_grid_unit_size = open_grid_unit_size
        self.module_height = module_height
        self.zip_tie_slot_length = zip_tie_slot_length
        self.zip_tie_slot_width = zip_tie_slot_width
        self.zip_tie_slot_depth = zip_tie_slot_depth
        self.bridge_top_width = bridge_top_width
        self.bridge_bottom_width = bridge_bottom_width
        self.bridge_thickness = bridge_thickness
        self.entry_slope_run = entry_slope_run
        self.outer_fillet_radius = outer_fillet_radius
        self.top_fillet_radius = top_fillet_radius
        self.bridge_fillet_radius = bridge_fillet_radius
        self.slope_floor_fillet_radius = slope_floor_fillet_radius
        self.snap_in_slot_cutter = snap_in_slot_cutter

        half_top = self.bridge_top_width / 2
        half_bottom = self.bridge_bottom_width / 2
        z_top = self.module_height
        z_bridge_bottom = self.module_height - self.bridge_thickness
        z_floor = self.module_height - self.zip_tie_slot_depth

        with BuildPart() as part:
            Box(
                self.open_grid_unit_size,
                self.open_grid_unit_size,
                self.module_height,
                align=(Align.CENTER, Align.CENTER, Align.MIN),
            )
            if self.outer_fillet_radius > 0:
                fillet(part.edges().filter_by(Axis.Z), radius=self.outer_fillet_radius)
            # Snap pocket from the bottom face; rotated to match RoundHead insertion
            # (wide pad toward the open face). Align.NONE on Y keeps the RoundHead
            # center on the unit-base origin (CENTER would shift the asymmetric cutter).
            self.snap_in_slot_cutter(
                rotation=(180, 0, 0),
                align=(Align.CENTER, Align.NONE, Align.MAX),
                mode=Mode.SUBTRACT,
            )
            # Rectangular pocket from the opposite (top) face.
            with Locations((0, 0, self.module_height)):
                Box(
                    self.zip_tie_slot_length,
                    self.zip_tie_slot_width,
                    self.zip_tie_slot_depth,
                    align=(Align.CENTER, Align.CENTER, Align.MAX),
                    mode=Mode.SUBTRACT,
                )
            # Trapezoid bridge: wider on top, narrower underneath so ±Y faces
            # slope and guide a zip tie under the bridge.
            with BuildSketch(Plane.YZ):
                with BuildLine():
                    Polyline(
                        (-half_top, z_top),
                        (half_top, z_top),
                        (half_bottom, z_bridge_bottom),
                        (-half_bottom, z_bridge_bottom),
                        close=True,
                    )
                make_face()
            extrude(amount=self.zip_tie_slot_length / 2, both=True)
            # Top-face entry ramps down to the slot floor so a tip can slide in
            # and back out without catching on a ledge.
            if self.entry_slope_run > 0:
                for sign in (-1, 1):
                    y_slot = sign * half_slot_width
                    y_outer = sign * (half_slot_width + self.entry_slope_run)
                    with BuildSketch(Plane.YZ):
                        with BuildLine():
                            Polyline(
                                (y_slot, z_top),
                                (y_outer, z_top),
                                (y_slot, z_floor),
                                close=True,
                            )
                        make_face()
                    extrude(
                        amount=self.zip_tie_slot_length / 2,
                        both=True,
                        mode=Mode.SUBTRACT,
                    )
            if self.slope_floor_fillet_radius > 0:
                slope_floor_edges = ShapeList(
                    e
                    for e in part.edges()
                    if abs(e.center().Z - z_floor) < 1e-2
                    and abs(e.length - self.zip_tie_slot_length) < 1e-2
                    and abs(abs(e.center().Y) - half_slot_width) < 1e-2
                )
                if slope_floor_edges:
                    fillet(slope_floor_edges, radius=self.slope_floor_fillet_radius)
            if self.bridge_fillet_radius > 0:
                bridge_under = ShapeList(
                    e
                    for e in part.edges()
                    if abs(e.center().Z - z_bridge_bottom) < 1e-2
                    and abs(e.length - self.zip_tie_slot_length) < 1e-2
                    and abs(e.center().Y) <= half_bottom + 1e-2
                )
                if bridge_under:
                    fillet(bridge_under, radius=self.bridge_fillet_radius)
            if self.top_fillet_radius > 0:
                top_edges = ShapeList(
                    e for e in part.edges() if abs(e.center().Z - z_top) < 1e-2
                )
                if top_edges:
                    fillet(top_edges, radius=self.top_fillet_radius)

        super().__init__(part.part, rotation=rotation, align=align, mode=mode)


def _with_version_mark(module: ZipTieModule):
    build_env = BuildEnv.from_local_git_repo()
    if not build_env.versioned_model_enabled:
        return module
    with BuildPart() as versioned:
        add(module)
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
    return Result(model=module, versioned=versioned)


@artifact(sample=True, short_desc="Zip-tie snap module for RoundHead mounting")
def zip_tie_module():
    """Unit box with snap-in slot pocket and opposite-face zip-tie bridge."""
    return _with_version_mark(ZipTieModule())
