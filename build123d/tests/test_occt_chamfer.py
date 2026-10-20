"""Shared AddDA construction, validity, and caller-specific fallback contracts."""
import math
from types import SimpleNamespace

import pytest
from build123d import Align, Box, Pos
from OCP.StdFail import StdFail_NotDone

import occt
from drawer import container, shell
from holders import cup_lid, gridfinity_shelf


@pytest.mark.parametrize("angle", [math.pi/4, math.radians(45.01)])
def test_one_builder_preserves_every_pair_and_angle(monkeypatch, angle):
    calls, builders = [], []
    shape = object()
    result = SimpleNamespace(is_valid=True)

    class Builder:
        def __init__(self, wrapped):
            builders.append(wrapped)

        def AddDA(self, *args):
            calls.append(args)

        def Shape(self):
            return shape

    def wrap(value):
        assert value is shape
        return result

    monkeypatch.setattr(occt, "BRepFilletAPI_MakeChamfer", Builder)
    monkeypatch.setattr(occt, "Part", wrap)
    part = SimpleNamespace(wrapped=object())
    pairs = [(SimpleNamespace(wrapped=object()), SimpleNamespace(wrapped=object()))
             for _ in range(3)]
    assert occt.angled_chamfer(part, pairs, .3, angle) is result
    assert builders == [part.wrapped]
    assert calls == [(.3, angle, edge.wrapped, face.wrapped) for edge, face in pairs]


def test_invalid_result_retains_edges_without_repair(monkeypatch):
    part = Box(10, 10, 10)
    face = part.faces().sort_by(lambda f: f.center().Z)[0]
    pairs = [(edge, face) for edge in face.edges()]
    monkeypatch.setattr(occt, "Part", lambda shape: SimpleNamespace(is_valid=False))
    with pytest.raises(occt.AngledChamferInvalid) as error:
        occt.angled_chamfer(part, pairs, .3, math.pi/4)
    assert error.value.edges == list(face.edges())
    assert not isinstance(error.value, (ValueError, StdFail_NotDone))


def test_not_done_propagates_from_helper(monkeypatch):
    error = StdFail_NotDone("injected")

    class Builder:
        def __init__(self, wrapped):
            pass

        def Shape(self):
            raise error

    monkeypatch.setattr(occt, "BRepFilletAPI_MakeChamfer", Builder)
    with pytest.raises(StdFail_NotDone) as caught:
        occt.angled_chamfer(Box(10, 10, 10), [], .3, math.pi/4)
    assert caught.value is error


def fail_with(error):
    def fail(*args):
        raise error
    return fail


@pytest.mark.parametrize("error", [occt.AngledChamferInvalid([]), StdFail_NotDone("injected")])
def test_container_failure_reaches_wedge(monkeypatch, error):
    part = Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    calls = []
    monkeypatch.setattr(container, "print_frame", lambda values: Pos())
    monkeypatch.setattr(container, "angled_chamfer", fail_with(error))

    def wedge(printed, edges):
        calls.append(edges)
        return part

    monkeypatch.setattr(container, "_wedge_bevel", wedge)
    result = container.chamfer_bed(part)
    assert len(calls) == 1 and len(calls[0]) == 4
    assert result.volume == pytest.approx(part.volume)


def test_container_rejects_multiple_solids(monkeypatch):
    monkeypatch.setattr(container, "angled_chamfer",
                        lambda *args: SimpleNamespace(solids=lambda: [object(), object()]))
    assert container._occt_bevel(Box(10, 10, 10), []) is None


@pytest.mark.parametrize("invalid", [False, True])
def test_shell_fallback_only_for_not_done(monkeypatch, invalid):
    part = Box(10, 10, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
    error = occt.AngledChamferInvalid([]) if invalid else StdFail_NotDone("injected")
    calls = []
    monkeypatch.setattr(shell, "AUTHOR_TO_MODEL", Pos())
    monkeypatch.setattr(shell, "source_back_magnet_positions", lambda values: [])
    monkeypatch.setattr(shell, "angled_chamfer", fail_with(error))
    monkeypatch.setattr(shell, "_bevel_from_sections", lambda source: calls.append(source) or part)
    if invalid:
        with pytest.raises(occt.AngledChamferInvalid) as caught:
            shell.chamfer_bed(part)
        assert caught.value is error
        assert calls == []
    else:
        assert shell.chamfer_bed(part).volume == pytest.approx(part.volume)
        assert len(calls) == 1


@pytest.mark.parametrize("module", [cup_lid, gridfinity_shelf])
def test_holder_invalid_chamfer_propagates(monkeypatch, module):
    error = occt.AngledChamferInvalid([])
    monkeypatch.setattr(module, "angled_chamfer", fail_with(error))
    with pytest.raises(occt.AngledChamferInvalid) as caught:
        module.SPEC.build({})
    assert caught.value is error


@pytest.mark.audit
def test_curved_shelf_bevel_margin_clears_production_threshold():
    """Pin the 45.01 margin on real curved shelf loops.

    The site's measured 45.0 curved nominal is ~45.0012, above 45.001;
    this is an overhang margin, not degeneration. A straight-loop 45.0
    container bevel also passes. Do not assert a kernel-specific overshoot.
    """
    from tests.print_audit import MAX_OVERHANG_DEG, _ANGLE_TOL_DEG, _max_overhang

    part = gridfinity_shelf.build({})
    printed = gridfinity_shelf.print_frame({}) * part
    # Only the bed-bevel band: the shelf's library slots have independent
    # exclusions in the complete production audit.
    bevels = [face for face in printed.faces()
              if face.bounding_box().min.Z < 1e-5
              and .1 < face.bounding_box().max.Z < .5]
    assert any(face.geom_type.name == "BSPLINE" for face in bevels)

    class BevelBand:
        def faces(self):
            return bevels

        def is_inside(self, *args, **kwargs):
            return printed.is_inside(*args, **kwargs)

    worst = _max_overhang(BevelBand(), (0, 0, 1), [], 0)
    assert 44.9 < worst <= MAX_OVERHANG_DEG + _ANGLE_TOL_DEG
