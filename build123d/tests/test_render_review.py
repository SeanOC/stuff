"""Offline tests for the ADVISORY render-review script (bead pst-3eun, Layer 2).

These exercise rubric selection, graceful degradation, and payload shape
WITHOUT calling OpenRouter — the network call is never made here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import render_review as rr  # noqa: E402
from holders.registry import KNOWN_MOUNTS  # noqa: E402


def test_every_known_mount_has_a_rubric():
    """A mount type with a deterministic contract should also have an advisory
    rubric, so the two layers stay in step."""
    assert set(KNOWN_MOUNTS) <= set(rr.RUBRICS)


def test_rubric_for_multiconnect_model():
    by_slug = rr._models_by_slug()
    # A shipped holder declares multiconnect-slot.
    slug = "holder-spray-can"
    assert slug in by_slug
    rubric, mounts = rr._rubric_for(slug, by_slug)
    assert mounts == ["multiconnect-slot"]
    assert any("bottom edge" in line.lower() for line in rubric)


def test_rubric_falls_back_to_generic_for_unknown_slug():
    rubric, mounts = rr._rubric_for("not-a-model", {})
    assert mounts == []
    assert rubric == rr._GENERIC_RUBRIC


def test_review_one_skips_without_api_key(tmp_path):
    """No key -> a skip note, no exception, no network."""
    png = tmp_path / "holder-spray-can.png"
    png.write_bytes(b"\x89PNG\r\n")  # not decoded when the key is absent
    out = rr.review_one(png, rr._models_by_slug(), api_key="", model="m")
    assert "skipped" in out.lower()
    assert "holder-spray-can" in out


def test_main_is_advisory_with_no_pngs():
    """Advisory: nothing to review still exits 0."""
    assert rr.main([]) == 0


def test_request_payload_shape(tmp_path):
    png = tmp_path / "holder-spray-can.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    payload = rr._request_payload(
        "holder-spray-can", png, ["Q1?"], ["multiconnect-slot"], "some-model"
    )
    assert payload["model"] == "some-model"
    content = payload["messages"][0]["content"]
    kinds = {c["type"] for c in content}
    assert kinds == {"text", "image_url"}
    img = next(c for c in content if c["type"] == "image_url")
    assert img["image_url"]["url"].startswith("data:image/png;base64,")
