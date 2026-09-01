"""ADVISORY render review — a vision model eyeballs the model PNGs (bead pst-3eun, Layer 2).

This is the *advisory* companion to the deterministic mount contracts
(tests/mount_contracts.py, Layer 1). The contracts gate; this never does.
It sends each model's 3-view render plus a mount-type rubric to a vision
model via OpenRouter and prints a Markdown summary (a human still decides).

Design constraints (plan review pst-swsu, point 3):
- ADVISORY ONLY. It exits 0 whatever the model says; it emits no required
  status and must never be wired as a required check.
- Degrades gracefully with no OPENROUTER_API_KEY (prints a skip note, exits 0),
  so it is safe on forks and on PRs from contributors without the secret.
- Model output is clearly labelled advisory and is never parsed for a verdict.

Usage
-----
    python scripts/render_review.py out/holder_spray_can.png out/holder_bottle_500ml.png
    python scripts/render_review.py --models-dir out            # every <slug>.png in out/

The rubric for each PNG is chosen from the model's declared ``mounts`` in the
registry (slug -> spec). A PNG with no matching model, or a model with no
mount, gets a generic "does this look like a sane, printable holder?" rubric.

Env:
    OPENROUTER_API_KEY   required to actually call the model (else skip)
    RENDER_REVIEW_MODEL  override the model id (default below)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from holders.registry import all_models  # noqa: E402

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3-vl-235b-a22b-instruct"  # vision model (inx assess.ts pattern)

# Mount-type -> the checklist a reviewer applies to the render. Keyed by the
# same names as registry.KNOWN_MOUNTS so a new mount contract can add its rubric
# alongside its deterministic check.
RUBRICS: dict[str, list[str]] = {
    "multiconnect-slot": [
        "Does the Multiconnect slot channel reach the BOTTOM edge of the back "
        "plate (an open mouth a wall head can slide into), rather than being a "
        "sealed pocket?",
        "Does the slot opening face DOWN (-Z), so the holder lowers onto the "
        "wall head — not up?",
        "Is there a solid FLOOR closing the bottom of the cylinder collar, so an "
        "item cannot drop straight through?",
    ],
}

_GENERIC_RUBRIC = [
    "Does this look like a sane, printable holder with no obviously broken, "
    "floating, or inside-out geometry?",
]


def _models_by_slug() -> dict:
    # Keyed by both slug (hyphens) and registry name (underscores): export.py
    # names PNGs by spec.name, gallery bakes by spec.slug.
    lookup: dict = {}
    for spec in all_models():
        lookup[spec.slug] = spec
        lookup[spec.name] = spec
    return lookup


def _rubric_for(slug: str, by_slug: dict) -> tuple[list[str], list[str]]:
    """(rubric lines, mount types) for a PNG named <slug>.png."""
    spec = by_slug.get(slug) or by_slug.get(slug.replace("_", "-"))
    if spec is None or not spec.mounts:
        return _GENERIC_RUBRIC, []
    lines: list[str] = []
    for mount in spec.mounts:
        lines.extend(RUBRICS.get(mount, []))
    return (lines or _GENERIC_RUBRIC), list(spec.mounts)


def _build_prompt(slug: str, rubric: list[str], mounts: list[str]) -> str:
    mount_note = (
        f"This model declares mount type(s): {', '.join(mounts)}. "
        if mounts
        else ""
    )
    checklist = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(rubric))
    return (
        f"You are reviewing orthographic + iso renders of a 3D-printed part "
        f"'{slug}'. {mount_note}The image tiles three views (iso, front, top).\n\n"
        f"Answer each check YES / NO / UNSURE with one sentence of reasoning:\n"
        f"{checklist}\n\n"
        f"End with a one-line overall note. This is an advisory sanity check, "
        f"not a pass/fail gate."
    )


def _encode_image(png: Path) -> str:
    data = base64.b64encode(png.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _request_payload(slug: str, png: Path, rubric: list[str], mounts: list[str], model: str) -> dict:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _build_prompt(slug, rubric, mounts)},
                    {"type": "image_url", "image_url": {"url": _encode_image(png)}},
                ],
            }
        ],
    }


def _call_openrouter(payload: dict, api_key: str, timeout: float = 90.0) -> str:
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"].strip()


def review_one(png: Path, by_slug: dict, api_key: str, model: str) -> str:
    """Return a Markdown section reviewing one PNG (never raises for API errors)."""
    slug = png.stem
    rubric, mounts = _rubric_for(slug, by_slug)
    header = f"### {slug}"
    if not api_key:
        return f"{header}\n\n_advisory review skipped: OPENROUTER_API_KEY not set._\n"
    try:
        payload = _request_payload(slug, png, rubric, mounts, model)
        answer = _call_openrouter(payload, api_key)
    except (urllib.error.URLError, KeyError, TimeoutError, OSError) as exc:
        return f"{header}\n\n_advisory review unavailable ({type(exc).__name__}): {exc}._\n"
    return f"{header}\n\n{answer}\n"


def _emit(markdown: str) -> None:
    print(markdown)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(markdown + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pngs", nargs="*", type=Path, help="model render PNGs (<slug>.png)")
    ap.add_argument("--models-dir", type=Path, help="review every <slug>.png in this dir")
    ap.add_argument("--model", default=os.environ.get("RENDER_REVIEW_MODEL", DEFAULT_MODEL))
    args = ap.parse_args(argv)

    pngs = list(args.pngs)
    if args.models_dir:
        pngs.extend(sorted(args.models_dir.glob("*.png")))
    if not pngs:
        print("no PNGs to review", file=sys.stderr)
        return 0  # advisory: nothing to do is not a failure

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    by_slug = _models_by_slug()

    parts = ["## Advisory render review", "", "_Vision-model sanity check — NOT a gate._", ""]
    for png in pngs:
        parts.append(review_one(png, by_slug, api_key, args.model))
    _emit("\n".join(parts))
    return 0  # ADVISORY: always succeed


if __name__ == "__main__":
    raise SystemExit(main())
