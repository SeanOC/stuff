"""The explicit E1 interface values; no hardware-fit claim or audit waiver."""
import pytest

from rack10 import constants as c


@pytest.mark.parametrize('name,expected', [
    ('RACK_UNIT', 44.45), ('HOLE_PITCH', 15.875), ('HOLE_EDGE', 6.35),
    ('EAR_WIDTH', 254), ('HOLE_SPAN', 236.525), ('CLEAR_OPENING', 222.25),
    ('USABLE_WIDTH', 210), ('CAGE_SQUARE', 9.525), ('PANEL_SHORT', 0.8),
    ('SCREW_CLEAR', 6.4), ('EAR_HOLE_D', 7), ('MAX_SLOT_MM', 8),
    ('PANEL_THICKNESS', 3), ('EAR_THICKNESS', 4),
    ('KEYSTONE_WIDTH', 14.5), ('KEYSTONE_HEIGHT', 16), ('KEYSTONE_PITCH', 19),
])
def test_rack10_interface_value(name, expected):
    assert getattr(c, name) == pytest.approx(expected)


def test_rack10_derived_limits():
    assert c.TRAY_OUTER_WIDTH_LIMIT == pytest.approx(220.25)
    assert c.MAX_KEYSTONES == 11
    assert c.MAX_KEYSTONES * c.KEYSTONE_PITCH <= c.USABLE_WIDTH
    assert (c.MAX_KEYSTONES + 1) * c.KEYSTONE_PITCH > c.USABLE_WIDTH


def test_rack10_specified_panel_and_hole_layout():
    assert c.RACK_UNIT - c.PANEL_SHORT == pytest.approx(43.65)
    assert [c.HOLE_EDGE + i * c.HOLE_PITCH for i in range(c.HOLES_PER_UNIT)] == pytest.approx(
        [6.35, 22.225, 38.1])
