"""Evaluate the holder's real SCAD sizing rules without rendering its mesh."""
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.invariants.params import parse_params

MODEL = Path(__file__).resolve().parents[1] / 'models/apple_tv_4th_gen_holder.scad'
PARAMS = parse_params(MODEL.read_text())


@unittest.skipUnless(shutil.which('openscad'), 'OpenSCAD is required')
class PlateRangeTest(unittest.TestCase):
    def dimensions(self, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'probe.scad'
            source.write_text(
                f'include <{MODEL}>\n'
                'echo(plate_probe=[units_w, units_h, W, H]);\n')
            command = ['openscad', '-o', str(Path(directory) / 'probe.csg')]
            for name, value in overrides.items():
                command += ['-D', f'{name}={json.dumps(value)}']
            result = subprocess.run(command + [str(source)], capture_output=True,
                                    text=True, check=True, timeout=60)
            self.assertNotIn('ERROR:', result.stderr)
            match = re.search(r'plate_probe = (\[[^\]]+\])', result.stderr)
            self.assertIsNotNone(match, result.stderr)
            return json.loads(match[1])

    def test_default_baseline(self):
        self.assertEqual(self.dimensions(), [4, 4, 112, 112])

    def test_every_declared_tile_value_changes_plate(self):
        for name, axis in [('width_units', 0), ('height_units', 1)]:
            spec = PARAMS[name]
            self.assertEqual(spec['min'], 4)
            previous = 0
            for value in range(int(spec['min']), int(spec['max']) + 1):
                with self.subTest(name=name, value=value):
                    dims = self.dimensions(**{name: value})
                    self.assertEqual(dims[axis], value)
                    self.assertEqual(dims[axis + 2], value * 28)
                    self.assertGreater(dims[axis + 2], previous)
                    previous = dims[axis + 2]

    def test_larger_device_auto_grows_both_axes(self):
        # Both dimensions are within the declared device range. The sliders
        # remain at 4 while the actual device floors grow to six tiles.
        width_floor = math.ceil((140 + 2 * 1 + 2 * 2.4) / 28)
        height_floor = math.ceil((4 + 140 + 1) / 28)
        self.assertEqual(self.dimensions(device_w=140, device_h=140),
                         [width_floor, height_floor, 168, 168])


if __name__ == '__main__':
    unittest.main()
