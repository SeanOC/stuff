"""HomeRacker lockpin: one watertight default, upstream envelope and volume.

Every preset is also compared to the pinned upstream reference in the wasm
sweep. Frame dimensions and tolerances must not drift when libraries change.
"""
from scripts.invariants import Failure, expect_connected_solids


def check(ctx):
    failures = expect_connected_solids(ctx, 1)
    expected = [8.0, 22.099998, 3.799999]
    if any(abs(got - want) > 0.01 for got, want in zip(ctx["bbox_mm"], expected)):
        failures.append(Failure("envelope", f"Expected {expected}, got {ctx['bbox_mm']}"))
    reference_volume = 305.407108
    if abs(ctx["stl"].volume / reference_volume - 1) > 0.001:
        failures.append(Failure("volume", "Default differs from pinned upstream by >0.1%"))
    if abs(ctx["stl"].bounds[0, 2]) > 0.01:
        failures.append(Failure("print-plane", "Default must rest on Z=0"))
    failures.extend(_check_native_plate())
    return failures


def _check_native_plate():
    """Catch CGAL scraps that the browser's vertex-connectivity check misses.

    Render with the same native exporter command as production. The default
    pin can be watertight even when translated copies generate zero-volume
    slivers, so the actual twenty-pin download needs its own topology check.
    """
    import os
    import subprocess
    from pathlib import Path
    from tempfile import TemporaryDirectory

    import trimesh

    root = Path(__file__).resolve().parent.parent
    with TemporaryDirectory(prefix="homeracker-plate-") as directory:
        output = Path(directory) / "plate.stl"
        try:
            result = subprocess.run(
                ["xvfb-run", "-a", "openscad", "-o", str(output),
                 "-D", "quantity=20", "-D", 'grip="standard"',
                 "-D", 'neck="none"', "-D", 'strength="regular"',
                 str(root / "models/homeracker_lockpin.scad")],
                env={**os.environ, "OPENSCADPATH": str(root / "libs")},
                capture_output=True, text=True, timeout=180,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [Failure("plate-export", str(exc))]
        if result.returncode or "ERROR:" in result.stderr or "WARNING:" in result.stderr:
            return [Failure("plate-export", result.stderr[-1500:])]
        mesh = trimesh.load(output, force="mesh")

    failures = []
    if not mesh.is_watertight:
        failures.append(Failure("plate-watertight", "Native twenty-pin STL is not watertight"))
    # Edge adjacency, without scipy/networkx (not installed in render CI).
    parents = list(range(len(mesh.faces)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in mesh.face_adjacency:
        parents[find(int(a))] = find(int(b))
    count = len({find(i) for i in range(len(mesh.faces))})
    if count != 20:
        failures.append(Failure("plate-count", f"Expected 20 solids, got {count}"))
    if any(abs(got - want) > 0.01 for got, want in zip(mesh.extents, [72, 130.1, 3.8])):
        failures.append(Failure("plate-envelope", f"Unexpected plate bbox: {mesh.extents}"))
    if abs(mesh.volume / (20 * 305.407108) - 1) > 0.001:
        failures.append(Failure("plate-volume", "Native plate differs from 20 upstream pins by >0.1%"))
    return failures
