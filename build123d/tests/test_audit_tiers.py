"""The PR tier is data-driven; corners and reproducers still run on main."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from holders.registry import Param, Preset, all_models
from tests.audit_tiers import pr_case

ROOT = Path(__file__).resolve().parents[1]
pytest_plugins = ['pytester']


def spec():
    # No geometry: the classifier only needs the registry parameter contract.
    from types import SimpleNamespace
    params = [Param('width', 'number', 5, min=1, max=10),
              Param('count', 'integer', 2, min=1, max=4),
              Param('mode', 'enum', 'normal', choices=('normal', 'other'))]
    presets = [Preset('wide-other', 'Wide other', {'width': 8, 'mode': 'other'})]
    def resolve(values=None):
        return {**{p.name: p.default for p in params}, **(values or {})}
    return SimpleNamespace(params=params, presets=presets, resolve_values=resolve)


@pytest.mark.parametrize('values', [{}, {'width':1}, {'width':10}, {'count':1},
                                     {'count':4}, {'width':10, 'count':2},
                                     {'width':8, 'mode':'other'}])
def test_defaults_presets_and_single_numeric_extremes_are_pr(values):
    assert pr_case(spec(), values)


@pytest.mark.parametrize('values', [{'width':8}, {'width':1, 'count':4},
                                     {'mode':'other'}, {'width':10, 'mode':'other'}])
def test_interior_hardware_modes_and_corners_are_full(values):
    assert not pr_case(spec(), values)


def test_large_tile_corners_are_full_and_single_extremes_are_pr():
    from holders.opengrid_tile import SPEC
    assert pr_case(SPEC, {'x_count':11})
    assert pr_case(SPEC, {'x_count':1, 'y_count':11, 'backing_mm':0})
    assert not pr_case(SPEC, {'x_count':6})
    assert not pr_case(SPEC, {'x_count':11, 'y_count':8})
    assert not pr_case(SPEC, {'x_count':8, 'y_count':11})
    assert not pr_case(SPEC, {'style':'lite', 'x_count':11, 'y_count':8})


def collected(expression, keyword=None):
    args = [sys.executable, '-m', 'pytest', 'tests/', '--collect-only',
            '-q', '--disable-warnings', '-m', expression]
    if keyword:
        args += ['-k', keyword]
    run = subprocess.run(args,
                         cwd=ROOT, text=True, capture_output=True, timeout=120)
    assert run.returncode == 0, run.stdout + run.stderr
    return {line for line in run.stdout.splitlines() if line.startswith('tests/') and '::' in line}


def test_live_collection_is_lossless_and_representative_cases_are_routed():
    pr = collected('audit and not audit_full and not upstream')
    full = collected('audit_full and not upstream')
    all_audits = collected('audit and not upstream')
    assert not pr & full
    assert pr | full == all_audits
    assert len(all_audits) >= 1229  # original 1227 plus the two large tile rows
    # Every registered model keeps a real default audit, independently of the
    # all-model bed gate. Inherited audit_full marks must not hide these either.
    for model in all_models():
        assert f'tests/test_print_audit.py::test_model_print_audit[{model.name}]' in pr

    # These carriers once lacked audit_case metadata and silently lost their
    # presets/defaults. Pin the actual node IDs, including every heavy mount
    # contract (each body checks defaults plus all registered presets).
    restored = {
        ('mount_contracts', 'model_mount_contract'): [
            'holder_spool_cradle:multibuild-multiconnect-channel',
            'holder_spool_cradle:openconnect-slot',
            'holder_spool_cradle:multibuild-fixpoint-slot',
            'openconnect_drawer:openconnect-slot-shallow'],
        ('openconnect_dividers', 'bed_chamfer_exception_does_not_reach_other_parts'): [
            'default', 'small', 'top-slot', 'container', 'two-compartments',
            'organiser', 'container-solid'],
        ('openconnect_dividers', 'new_presets_build'): [
            'two-compartments', 'organiser', 'stopper-clips'],
        ('spool_cradle', 'outboard_rear_end_has_no_knife'): ['default'],
        ('spool_cradle', 'inboard_cap_rear_end_has_no_knife'): ['default', 'channel-preset'],
        ('underware_path_channels', 'mitre_bed_flat'): [
            'mitre', 'mitre-r1', 'w1-h10-r0', 'w1-h22-r0', 'w1-h22-r1',
            'w1-h22-r2', 'w1-h72-r0', 'w4-h22-r0', 'length-7'],
    }
    for (module, function), cases in restored.items():
        expected = {f'tests/test_{module}.py::test_{function}[{case}]' for case in cases}
        assert expected <= pr, expected - pr
    for function in ('outboard', 'inboard_cap'):
        assert f'tests/test_spool_cradle.py::test_{function}_rear_end_has_no_knife[rear-land-corner]' in full
    assert 'tests/test_underware_path_channels.py::test_mitre_bed_flat[max-corner]' in full
    assert 'tests/test_cartridge_holder.py::test_presets[full_holder]' in pr
    assert 'tests/test_tombstone_sign.py::test_print_audit_per_preset[small]' in pr
    assert 'tests/test_opengrid_tile.py::test_endpoint_audit[full-6x6-back3]' in full
    assert 'tests/test_opengrid_tile.py::test_endpoint_audit[full-6x1-back0]' in full
    assert 'tests/test_opengrid_tile.py::test_endpoint_audit[lite-11x8-back1]' in full
    assert 'tests/test_opengrid_tile.py::test_endpoint_audit[full-1x11-back0]' in pr
    assert 'tests/test_spool_cradle.py::test_production_print_audit[diagonal-root-corner]' in full
    # A model with five presets and nine numeric parameters: at most the
    # default + presets + two endpoints per parameter; never its corners.
    saddle = {n for n in pr if n.startswith('tests/test_bench_width_saddle.py::test_endpoint_audit[')}
    assert len(saddle) == 23
    assert not any('test_unreachable_endpoints_raise' in n for n in all_audits)
    scoped = collected('audit and not audit_full and not upstream',
                       'bench_width_saddle or test_registry_presets_fit_bed')
    beds = {n for n in pr if '::test_registry_presets_fit_bed[' in n}
    assert len(beds) >= 106
    assert beds <= scoped
    assert len(scoped - beds) == 24


def test_selected_extreme_failure_still_fails_pr(pytester):
    path = ROOT/'tests/conftest.py'
    loader = importlib.util.spec_from_file_location('tier_hooks', path)
    hooks = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(hooks)
    pytester.makeini('[pytest]\nmarkers =\n    audit\n    audit_full\n    audit_case\n    audit_pr\n')
    pytester.makepyfile('''
import pytest
from tests.audit_tiers import audit_cases
from tests.test_audit_tiers import spec
@pytest.mark.audit
@pytest.mark.audit_full
@pytest.mark.parametrize('values', [{'width': 10}, {'width': 8}])
@audit_cases(spec())
def test_geometry(values):
    assert False, 'print guideline violation'
''')
    result = pytester.runpytest('-q', '-m', 'audit and not audit_full', plugins=[hooks])
    result.assert_outcomes(failed=1, deselected=1)
