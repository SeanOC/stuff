"""Hash the shared monokini module bodies across the staged Underware sources.

The Underware for openGrid upload (CC BY-NC-SA 4.0) is not vendored here
(epic pst-fsk8s, D0 outcome (b)); its 13 SCAD files are staged outside the
repository. This script records, per file, a SHA256 of each shared module or
function body with whitespace and // comments normalised, so
tests/test_underware.py can pin which copies are identical to
monokini_I_channel.scad without the source being committed.

    uv run python scripts/underware_module_hashes.py <staged dir> > tests/underware_module_hashes.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

NAMES = ('monokiniGrip', 'monokiniChannel', 'monokiniGripFlared',
         'monokiniGripFlaredCut', 'monokini_offset_profile',
         'monokini_midline_points', 'monokini_midline_rects')
REFERENCE = 'monokini_I_channel.scad'


def _strip(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def bodies(text: str) -> dict[str, str]:
    """Normalised source of every NAMES module/function in text."""
    text = _strip(text)
    found = {}
    for name in NAMES:
        m = re.search(r'\b(module|function) ' + name + r'\s*\(', text)
        if not m:
            continue
        start = m.start()
        if m.group(1) == 'module':
            i = text.index('{', m.end())
            depth = 0
            for j in range(i, len(text)):
                depth += {'{': 1, '}': -1}.get(text[j], 0)
                if depth == 0:
                    found[name] = text[start:j + 1]
                    break
        else:  # function bodies end at the first ';' at bracket depth 0
            depth = 1  # m.end() is just past the parameter list's '('
            for j in range(m.end(), len(text)):
                depth += {'(': 1, '[': 1, ')': -1, ']': -1}.get(text[j], 0)
                if text[j] == ';' and depth == 0:
                    found[name] = text[start:j + 1]
                    break
    return found


def table(directory: Path) -> dict:
    files = sorted(directory.glob('*.scad'))
    out = {'reference': REFERENCE, 'files': {}}
    for path in files:
        raw = path.read_bytes()
        out['files'][path.name] = {
            'sha256': hashlib.sha256(raw).hexdigest(),
            'modules': {k: hashlib.sha256(v.encode()).hexdigest()[:16]
                        for k, v in sorted(bodies(raw.decode()).items())},
        }
    ref = out['files'][REFERENCE]['modules']
    out['divergences'] = {
        name: sorted(n for n, f in out['files'].items()
                     if name in f['modules'] and f['modules'][name] != ref[name])
        for name in NAMES}
    return out


if __name__ == '__main__':
    json.dump(table(Path(sys.argv[1])), sys.stdout, indent=1, sort_keys=True)
    print()
