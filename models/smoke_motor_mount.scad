// Smoke-test plate: rectangular base with a centered bore + boss and
// four counter-bored mounting holes. Used as the smallest end-to-end
// model for the parametric pipeline.

$fn = 96;
PRINT_ANCHOR_BBOX = [60, 40, 5];

// === User-tunable parameters ===
plate_w   = 60;    // @param number min=20 max=200 step=1 label="Plate width (mm)"
plate_d   = 40;    // @param number min=20 max=200 step=1 label="Plate depth (mm)"
plate_t   = 5;     // @param number min=2 max=20 step=0.5 label="Plate thickness (mm)"
bore      = 20;    // @param number min=4 max=60 step=0.5 label="Center bore diameter (mm)"
boss      = 2;     // @param number min=0 max=10 step=0.5 label="Boss height (mm)"
hole_d    = 3.2;   // @param number min=2 max=10 step=0.1 label="Mount hole diameter (mm)"
hole_dx   = 48;    // @param number min=10 max=180 step=1 label="Mount hole spacing X (mm)"
hole_dy   = 28;    // @param number min=10 max=180 step=1 label="Mount hole spacing Y (mm)"
cb_d      = 6;     // @param number min=3 max=12 step=0.5 label="Counterbore diameter (mm)"
cb_depth  = 2;     // @param number min=0 max=8 step=0.5 label="Counterbore depth (mm)"

difference() {
    union() {
        translate([-plate_w/2, -plate_d/2, 0])
            cube([plate_w, plate_d, plate_t]);
        cylinder(h = plate_t + boss, d = bore + 6);
    }
    translate([0, 0, -1]) cylinder(h = plate_t + boss + 2, d = bore);
    for (sx = [-1, 1]) for (sy = [-1, 1]) {
        translate([sx * hole_dx/2, sy * hole_dy/2, -1])
            cylinder(h = plate_t + boss + 2, d = hole_d);
        translate([sx * hole_dx/2, sy * hole_dy/2, plate_t - cb_depth])
            cylinder(h = cb_depth + 0.1, d = cb_d);
    }
}
