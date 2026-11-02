"""CLI: `python -m bridge print ...` runs the same Bridge.start_print as POST /print,
then polls the run; `python -m bridge serve` starts the HTTP service.

`print` exit codes: 0 run completed (or --no-wait accepted); 1 start rejected or
run ended failed/partial_failure/cancelled; 2 bad config; 3 --max-wait elapsed
before a terminal state; 4 polling failed (Bambuddy errored or unreachable) -
the run's outcome is unknown, not failed."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

import httpx

from .config import ConfigError, load_config
from .core import TERMINAL_RUN_STATES, Bridge, BridgeError
from .spools import global_slot

EXIT_MAX_WAIT = 3
EXIT_POLL_ERROR = 4

HOST = "127.0.0.1"  # load-bearing: only tailscale serve may reach the service


def parse_param(raw: str) -> tuple[str, Any]:
    """k=v; v is JSON when it parses (numbers, booleans), else the plain string."""
    key, sep, value = raw.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"--param {raw!r} is not k=v")
    try:
        return key, json.loads(value)
    except ValueError:
        return key, value


def parse_spool(raw: str) -> dict[str, int]:
    try:
        ams, tray = (int(v) for v in raw.split("/"))
    except ValueError:
        raise argparse.ArgumentTypeError("--spool must be <ams_id>/<tray_id>") from None
    if global_slot(ams, tray) is None:
        raise argparse.ArgumentTypeError("--spool must identify an AMS tray (external excluded)")
    return {"ams_id": ams, "tray_id": tray}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m bridge")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("print", help="print a stuff model through a Bambuddy pipeline")
    p.add_argument("--source", choices=["bd", "scad"], required=True)
    p.add_argument("--slug", help="build123d slug (--source bd)")
    p.add_argument("--model", help="models/<stem>.scad or bare stem (--source scad)")
    p.add_argument("--preset")
    p.add_argument("--param", action="append", type=parse_param, default=[], metavar="K=V")
    p.add_argument("--printer-id", type=int, required=True)
    p.add_argument("--spool", type=parse_spool, metavar="AMS/TRAY")
    p.add_argument("--copies", type=int, default=1)
    p.add_argument("--poll-interval", type=float, default=10.0, help="seconds between run polls")
    p.add_argument("--no-wait", action="store_true", help="print the 202 body and exit")
    p.add_argument(
        "--max-wait",
        type=float,
        default=None,
        metavar="SECONDS",
        help="stop polling after this long, print the last status and exit 3 "
        "(default: wait until the run is terminal)",
    )

    sp = sub.add_parser("spools", help="list loaded AMS spools and resolved presets")
    sp.add_argument("--printer-id", type=int, required=True)

    s = sub.add_parser("serve", help="run the HTTP service on 127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    return ap


async def run_print(
    args: argparse.Namespace, transport: httpx.AsyncBaseTransport | None = None
) -> int:
    bridge = Bridge(load_config(), transport=transport)
    try:
        try:
            accepted = await bridge.start_print(
                source=args.source,
                slug=args.slug,
                model=args.model,
                preset=args.preset,
                params=dict(args.param) or None,
                printer_id=args.printer_id,
                copies=args.copies,
                spool=args.spool,
            )
        except BridgeError as e:
            print(json.dumps({"status": e.status, **e.payload}, indent=2), file=sys.stderr)
            return 1
        print(json.dumps(accepted, indent=2), flush=True)
        if args.no_wait:
            return 0
        return await poll(bridge, accepted["status_url"], args.poll_interval, args.max_wait)
    finally:
        await bridge.aclose()


async def poll(bridge: Bridge, status_url: str, interval: float, max_wait: float | None) -> int:
    loop = asyncio.get_running_loop()
    deadline = None if max_wait is None else loop.time() + max_wait
    last: dict[str, Any] | None = None
    label = (
        "run " + status_url.removeprefix("/runs/")
        if status_url.startswith("/runs/")
        else status_url
    )
    while True:
        try:
            state = await bridge.status(status_url)
        except (BridgeError, httpx.HTTPError) as e:
            cause = e.payload if isinstance(e, BridgeError) else {"error": type(e).__name__}
            print(
                json.dumps({"error": f"polling {label} failed", "cause": cause, "last": last}),
                file=sys.stderr,
            )
            return EXIT_POLL_ERROR
        if state != last:
            print(json.dumps(state), flush=True)
            last = state
        if state["status"] in TERMINAL_RUN_STATES:
            return 0 if state["status"] == "completed" else 1
        if deadline is not None and loop.time() >= deadline:
            print(
                json.dumps({"error": f"--max-wait {max_wait:g}s elapsed", "last": last}),
                file=sys.stderr,
            )
            return EXIT_MAX_WAIT
        pause = interval if deadline is None else min(interval, deadline - loop.time())
        await asyncio.sleep(max(pause, 0))


async def run_spools(args: argparse.Namespace) -> int:
    bridge = Bridge(load_config())
    try:
        print(json.dumps(await bridge.spools(args.printer_id), indent=2))
        return 0
    except BridgeError as e:
        print(json.dumps({"status": e.status, **e.payload}), file=sys.stderr)
        return 1
    finally:
        await bridge.aclose()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per poll otherwise
    try:
        if args.command == "print":
            return asyncio.run(run_print(args))
        if args.command == "spools":
            return asyncio.run(run_spools(args))
        import uvicorn

        from .app import create_app

        uvicorn.run(create_app(), host=HOST, port=args.port)
        return 0
    except ConfigError as e:
        print(f"bridge: refusing to start: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
