"""One rule for the PR audit tier; every other audit remains in the full sweep.

Test generators supply their spec and parameter values, not a tier override.
Compare resolved values so spelling defaults explicitly cannot turn an extreme
into a corner. Presets take precedence over the one-parameter rule.
"""
import pytest


def pr_case(spec, overrides):
    values = spec.resolve_values(overrides)
    if any(values == spec.resolve_values(p.values) for p in spec.presets):
        return True
    defaults = spec.resolve_values()
    changed = [p for p in spec.params if values[p.name] != defaults[p.name]]
    if not changed:
        return True
    return (len(changed) == 1 and changed[0].kind in ('number', 'integer')
            and values[changed[0].name] in (changed[0].min, changed[0].max))


def audit_cases(spec, values=lambda p: p['values']):
    """Attach collection-time metadata to an existing parametrized audit.

`spec` may be a resolver for tests spanning multiple registered models. The
values resolver reads pytest callspec params without building any geometry.
"""
    return pytest.mark.audit_case(spec, values)


def classify(item):
    """Keep existing node IDs and assertions; only change their job marker."""
    case = item.get_closest_marker('audit_case')
    if case:
        params = item.callspec.params
        spec, values = case.args
        spec = spec(params) if callable(spec) else spec
        keep = pr_case(spec, values(params))
    else:
        keep = item.get_closest_marker('audit_pr') is not None
    if keep:
        # Historical full-only presets now belong to the PR tier too. These
        # are item/function marks, never module-wide audit_full marks.
        item.own_markers[:] = [m for m in item.own_markers if m.name != 'audit_full']
    elif not item.get_closest_marker('audit_full'):
        item.add_marker(pytest.mark.audit_full)
