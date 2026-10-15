"""Argument parsing and the output/exit-code contract (pst-ptl41 C4).

Every subcommand prints a one-line human summary (``bd audit`` follows it
with the report block) or, with --json, exactly one JSON object. Exit 0 on
success, 1 when the verdict fails (audit, bed fit), 2 on usage or param
errors.
"""

from __future__ import annotations

import argparse
import json
import sys

from bd import audit, build, extent

SUBCOMMANDS = {"build": build, "audit": audit, "extent": extent}


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse exits 2; keep it, shorter text
        self.print_usage(sys.stderr)
        self.exit(2, f"bd: error: {message}\n")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--preset", help="a preset id of the model")
    p.add_argument("--param", action="append", default=[], metavar="K=V",
                   help="override one param (repeatable)")
    p.add_argument("--rebuild", action="store_true",
                   help="rebuild even when the part is cached")
    p.add_argument("--json", action="store_true", help="print one JSON object")


def parser() -> argparse.ArgumentParser:
    p = _Parser(prog="python -m bd",
                description="Build a registered build123d model once into a cached "
                            "BREP, then query it. NOT the beads tracker's bd.")
    sub = p.add_subparsers(dest="command", required=True, parser_class=_Parser)
    b = sub.add_parser("build", help="build into the part cache; print the key")
    b.add_argument("slug", help="model slug or name (see manifest.json)")
    _common(b)
    for name, text in (("audit", "print audit (tests/print_audit.py audit())"),
                       ("extent", "print-frame extent + bed verdict")):
        q = sub.add_parser(name, help=text)
        q.add_argument("target", help="a cache key from `bd build`, or a model slug")
        _common(q)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        code, summary, payload = SUBCOMMANDS[args.command].run(args)
    except build.UsageError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"bd: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, sort_keys=True) if args.json else summary)
    return code
