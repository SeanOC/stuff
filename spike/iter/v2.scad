// Turn 1 edit: fix hole spacing (D2) and add counterbores (D3).
// Leaving bore_dia unchanged pending dimensional verification.

$fn = 50;

plate_w = 60;
plate_d = 40;
plate_t = 5;

bore_dia = 20;    // FIXED: was 22 (caught by pixel measurement, not eyeball)

boss_dia = 25;
boss_h   = 2;

hole_dia     = 3.2;
hole_dx      = 50;   // FIXED: was 60
hole_dy      = 30;

cbore_dia    = 6;    // ADDED
cbore_depth  = 3;    // ADDED

module motor_mount() {
    difference() {
        union() {
            translate([-plate_w/2, -plate_d/2, 0])
                cube([plate_w, plate_d, plate_t]);
            translate([0, 0, plate_t])
                cylinder(h = boss_h, d = boss_dia);
        }
        translate([0, 0, -0.5])
            cylinder(h = plate_t + boss_h + 1, d = bore_dia);
        for (x = [-hole_dx/2, hole_dx/2])
            for (y = [-hole_dy/2, hole_dy/2]) {
                translate([x, y, -0.5])
                    cylinder(h = plate_t + 1, d = hole_dia);
                translate([x, y, plate_t - cbore_depth])
                    cylinder(h = cbore_depth + 0.5, d = cbore_dia);
            }
    }
}

motor_mount();
