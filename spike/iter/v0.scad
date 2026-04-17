// Motor mount plate -- first-pass attempt from prompt.
// Parametric. Plate sits with its bottom face at z=0, boss rises from top.

$fn = 50;

// --- Parameters ---
plate_w = 60;   // X extent
plate_d = 40;   // Y extent
plate_t = 5;    // plate thickness

bore_dia   = 20;
boss_dia   = 25;
boss_h     = 2;

hole_dia      = 3.2;
hole_dx       = 50;  // X spacing of mounting holes
hole_dy       = 30;  // Y spacing of mounting holes

cbore_dia     = 6;
cbore_depth   = 3;

module motor_mount() {
    difference() {
        union() {
            // base plate centered on origin in X/Y, bottom at z=0
            translate([-plate_w/2, -plate_d/2, 0])
                cube([plate_w, plate_d, plate_t]);
            // raised boss above the bore
            translate([0, 0, plate_t])
                cylinder(h = boss_h, d = boss_dia);
        }
        // motor bore -- through plate + boss
        translate([0, 0, -0.5])
            cylinder(h = plate_t + boss_h + 1, d = bore_dia);
        // four mounting holes with counterbores
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
