// Motor mount plate -- PERTURBED first pass.
// Evaluator knowingly injects 3 defects here; Author (Claude) must identify
// and fix each over the iteration loop using only PNG renders + spec.
//
// Hidden defects (DO NOT reveal in Author prompt):
//   D1: bore diameter 22 (spec: 20)   -- ~10% oversize, subtle visually
//   D2: hole_dx = 60   (spec: 50)     -- holes spaced too wide in X
//   D3: counterbores omitted entirely -- should be 6mm dia x 3mm deep

$fn = 50;

plate_w = 60;
plate_d = 40;
plate_t = 5;

bore_dia = 22;     // D1 defect: spec says 20

boss_dia = 25;
boss_h   = 2;

hole_dia = 3.2;
hole_dx  = 60;     // D2 defect: spec says 50
hole_dy  = 30;

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
                // D3 defect: counterbores omitted entirely
            }
    }
}

motor_mount();
