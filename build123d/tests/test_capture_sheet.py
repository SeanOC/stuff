"""Reference-sheet asset contracts, independent of PDF generation timestamps."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_sheet_manifest_roundtrip():
    source = ROOT/'build123d/capture/sheets.json'
    public = ROOT/'public/capture'
    assert source.read_bytes() == (public/'sheets.json').read_bytes()
    sheets = json.loads(source.read_text())
    assert set(sheets) == {'letter-v1', 'a4-v1'}
    for sheet_id, sheet in sheets.items():
        assert sheet['id'] == sheet_id
        assert sheet['dictionary'] == 'DICT_4X4_50'
        assert set(sheet['markers_mm']) == {'0', '1', '2', '3'}
        assert sheet['marker_size_mm'] == 24
        assert sheet['check_bar_mm']['length_mm'] == 100
        pdf = public/sheet['pdf']
        assert pdf.read_bytes().startswith(b'%PDF-')
        assert hashlib.sha256(pdf.read_bytes()).hexdigest() == sheet['pdf_sha256']


def test_sheet_manifest_matches_generator_constants():
    pytest.importorskip('cv2')
    spec = importlib.util.spec_from_file_location(
        'make_capture_sheet', ROOT/'build123d/scripts/make_capture_sheet.py')
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    sheets = json.loads((ROOT/'build123d/capture/sheets.json').read_text())
    for name in generator.SHEETS:
        generated = generator.manifest(name)
        stored = sheets[generated['id']]
        assert generated == {k: v for k, v in stored.items()
                             if k not in ('pdf', 'pdf_sha256')}
