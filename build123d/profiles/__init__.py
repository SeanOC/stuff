"""Printer profiles for the multi-colour 3MF download (pst-jyey1).

A profile turns the generic 3MF (scripts/export.py export_3mf_one_object)
into a slicer project: scripts/export.py apply_printer_profile copies the
generic file and adds the profile's full project config, so Bambu Studio's
"Load with settings" opens with the printer, the process, the filament
presets and our part colours already mapped. The generic 3MF is unchanged.

Each profile is a directory holding the config exported from the slicer
itself; README.md records provenance and the how-to-add-a-printer recipe.
The ids reach the web app through manifest.json (printerProfiles), so the
app never hardcodes them.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PrinterProfile:
    id: str
    display_name: str
    slicer: str  # only "bambu-studio" so far
    template: Path  # the slicer's full project config (flat JSON)
    filament_slots: int  # the template's filament count; a model may use fewer
    application: str  # 3dmodel.model Application metadata, copied from the template's own

    def settings(self) -> dict:
        """A fresh copy of the template config (callers mutate it)."""
        return json.loads(self.template.read_text(encoding='utf-8'))


PROFILES: dict[str, PrinterProfile] = {
    p.id: p for p in (
        PrinterProfile(
            id='bambu-h2c-0.4',
            display_name='Bambu Lab H2C (0.4 mm nozzle)',
            slicer='bambu-studio',
            template=ROOT / 'bambu-h2c-0.4' / 'project_settings.json',
            filament_slots=8,
            # Must match the config's "version" key (02.08.02.61): Bambu Studio
            # only reads project_settings.config when Application starts with
            # "BambuStudio-" (bbs_3mf.cpp, m_is_bbl_3mf).
            application='BambuStudio-02.08.02.61',
        ),
    )
}
