"""Tests for scripts/invariants/params.py.

Focused on the `filename` opt-in flag (st-sq6) which drives the
export-all filename grid. The pre-existing parser behavior is covered
by lib/scad-params/parse.test.ts (the TS parser this module mirrors).
"""

from __future__ import annotations

import textwrap

from scripts.invariants.params import filename_export_params, parse_params


def _wrap(body: str) -> str:
    return textwrap.dedent(
        f"""\
        // === User-tunable parameters ===

        {body}

        // === Internals ===
        cube([1,1,1]);
        """
    )


def test_filename_flag_detected_on_enum():
    src = _wrap(
        'part = "assembly";  // @param enum choices=assembly|base|cap '
        'group=part label="Which piece" filename'
    )
    params = parse_params(src)
    assert params["part"]["filename"] is True
    assert params["part"]["choices"] == ["assembly", "base", "cap"]


def test_filename_absent_by_default():
    src = _wrap('mode = "round"; // @param enum choices=round|square')
    params = parse_params(src)
    assert "filename" not in params["mode"]


def test_filename_does_not_collide_with_label_containing_word():
    # A label containing the word "filename" must not trip the bare-flag scan.
    src = _wrap(
        'mode = "a"; // @param enum choices=a|b label="contains filename in label"'
    )
    params = parse_params(src)
    # The bare-flag regex requires whitespace boundaries on both sides, so
    # the trailing `"` of the quoted label keeps the word out. Confirm:
    assert "filename" not in params["mode"]


def test_filename_export_params_orders_by_declaration():
    src = _wrap(
        'a = "x"; // @param enum choices=x|y filename\n'
        '        b = "p"; // @param enum choices=p|q filename\n'
        '        c = "k"; // @param enum choices=k|l'
    )
    params = parse_params(src)
    assert filename_export_params(params) == [
        ("a", ["x", "y"]),
        ("b", ["p", "q"]),
    ]


def test_filename_export_params_ignores_non_enum():
    # `filename` on a non-enum is meaningless — no choices to expand.
    src = _wrap("count = 4; // @param integer filename")
    params = parse_params(src)
    # Parser still records the flag, but the export helper skips it.
    assert params["count"].get("filename") is True
    assert filename_export_params(params) == []


def test_filename_export_params_empty_when_no_flags():
    src = _wrap('mode = "r"; // @param enum choices=r|s')
    assert filename_export_params(parse_params(src)) == []
