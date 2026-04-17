// Spike v0: hand-written to match GROUND_TRUTH.md.
// Intentionally clean — the iteration loop will perturb this and measure
// whether Claude can drive it back to spec using only multi-angle PNGs.

$fn = 96;

// --- parameters ---
plate_x       = 60;
plate_y       = 40;
plate_z       = 5;

bore_d        = 20;
boss_od       = 25;
boss_h        = 2;

hole_d        = 3.2;
cbore_d       = 6;
cbore_depth   = 3;

hole_spacing_x = 50;
hole_spacing_y = 30;

// --- geometry ---
module mount() {
    difference() {
        union() {
            // base plate, centered at origin, top face at z=plate_z
            translate([0, 0, plate_z / 2])
                cube([plate_x, plate_y, plate_z], center = true);
            // raised boss around the motor bore
            translate([0, 0, plate_z])
                cylinder(h = boss_h, d = boss_od);
        }
        // central motor bore, through plate + boss, with slop for clean preview
        translate([0, 0, -1])
            cylinder(h = plate_z + boss_h + 2, d = bore_d);
        // four mounting holes with top-face counterbores
        for (sx = [-1, 1]) for (sy = [-1, 1]) {
            translate([sx * hole_spacing_x / 2, sy * hole_spacing_y / 2, 0]) {
                translate([0, 0, -1])
                    cylinder(h = plate_z + 2, d = hole_d);
                translate([0, 0, plate_z - cbore_depth])
                    cylinder(h = cbore_depth + 1, d = cbore_d);
            }
        }
    }
}

mount();
