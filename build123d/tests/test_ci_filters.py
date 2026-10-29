"""pst-was5b: bd123's `cradle` paths filter must cover every audit_full carrier.

A PR runs the `build123d audit (full sweep)` job only when it touches a path in
the dorny/paths-filter `cradle:` block of .github/workflows/bd123.yml (main and
nightly always run it). A test file that carries an audit_full case, or a
tests/ helper such a file imports, missing from that block means a PR changing
only that file merges without ever running its sweep — the gap PR #249's review
found for test_audit_record.py. Text parsing on purpose: pyyaml is only a
transitive dependency, and the filter body is a YAML string inside YAML.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT/'tests'
WORKFLOW = ROOT.parent/'.github'/'workflows'/'bd123.yml'

_MARK = re.compile(r'\bmark\.audit_full\b')
_IMPORT = re.compile(r'^\s*(?:from\s+(?:tests\.)?(\w+)\s+import\s+([\w\s,()]+)|import\s+(?:tests\.)?(\w+))')


def cradle_filter(text):
    """The quoted entries of the `cradle:` list, in order."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == 'cradle:' and 'filters' in lines[i - 1])
    indent = len(lines[start + 1]) - len(lines[start + 1].lstrip())
    entries = []
    for line in lines[start + 1:]:
        body = line.strip()
        if body and len(line) - len(line.lstrip()) < indent:
            break
        if body.startswith('- '):
            entries.append(body[2:].strip().strip('\'"'))
    return entries


def _code(path):
    return [line for line in path.read_text().splitlines() if not line.lstrip().startswith('#')]


def audit_full_carriers():
    return sorted(p for p in TESTS.glob('test_*.py') if any(_MARK.search(line) for line in _code(p)))


def _local_imports(path):
    """tests/ modules `path` imports directly (`from tests import x`, `from tests.x
    import y`, or a bare `import x` / `from x import y` resolved via sys.path)."""
    names = set()
    for line in _code(path):
        m = _IMPORT.match(line)
        if not m:
            continue
        module, imported, bare = m.groups()
        if module == 'tests':
            names.update(n for n in re.findall(r'\w+', imported) if n != 'as')
        else:
            names.add(module or bare)
    return {TESTS/f'{n}.py' for n in names if (TESTS/f'{n}.py').is_file()}


def required_paths():
    """Every audit_full carrier plus the tests/ helpers it imports, transitively."""
    todo, seen = list(audit_full_carriers()), set()
    while todo:
        path = todo.pop()
        if path not in seen:
            seen.add(path)
            todo.extend(_local_imports(path) - seen)
    return sorted(seen)


def _covered(path, entries):
    rel = path.relative_to(ROOT.parent).as_posix()
    return any(rel == e or (e.endswith('/**') and rel.startswith(e[:-2])) for e in entries)


def test_cradle_filter_parses():
    entries = cradle_filter(WORKFLOW.read_text())
    assert 'build123d/tests/print_audit.py' in entries and 'build123d/uv.lock' in entries, entries


def test_cradle_filter_entries_exist():
    """A stale or misspelt entry silently matches nothing."""
    for entry in cradle_filter(WORKFLOW.read_text()):
        target = ROOT.parent/entry.removesuffix('/**')
        assert target.exists(), entry


def test_cradle_filter_covers_every_audit_full_carrier():
    carriers = audit_full_carriers()
    assert TESTS/'test_spool_cradle.py' in carriers and TESTS/'test_audit_record.py' in carriers
    entries = cradle_filter(WORKFLOW.read_text())
    missing = [p.relative_to(ROOT.parent).as_posix() for p in required_paths() if not _covered(p, entries)]
    assert not missing, f'add to the cradle: filter in {WORKFLOW.name}: {missing}'
