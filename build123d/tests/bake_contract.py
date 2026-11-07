"""Expected artifact keys shared by bake output and baseline coverage checks."""
from holders.registry import resolve_colour_parts
from profiles import PROFILES
from scripts.geometry_baseline import preset_specs


def expected_bake_keys() -> set[str]:
    """Return relative POSIX paths for every app-listed preset's artifacts."""
    keys = set()
    for spec, preset in preset_specs():
        stem = f"{spec.slug}/{preset.id}"
        keys.update(f"{stem}.{ext}" for ext in ("stl", "glb", "png"))
        if spec.is_multi_colour:
            keys.add(f"{stem}.3mf")
            keys.update(f"{stem}.{profile}.3mf" for profile in PROFILES)
            keys.update(f"{stem}-{name}.stl"
                        for name, _, _ in resolve_colour_parts(spec, preset.values))
    return keys
