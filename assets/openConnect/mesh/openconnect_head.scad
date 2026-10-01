// Not upstream: renders mitufy's openconnect_head() (lib/openconnect_lib.scad)
// as the reference for build123d/tests/test_openconnect.py. Resolution
// matches openconnect_plate.scad.
$fa = 1;
$fs = 0.4;
include <../lib/opengrid_base.scad>
use <../lib/openconnect_lib.scad>

openconnect_head(head_type="head", add_nubs="Both");
