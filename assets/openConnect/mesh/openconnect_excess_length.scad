// Reference wrapper, not upstream. openConnect by mitufy, CC BY 4.0.
$fa = 1;
$fs = 0.4;
include <../lib/opengrid_base.scad>
use <../lib/openconnect_lib.scad>
openconnect_slot_grid(slot_lock_distribution="All", excess_length=5.0);
