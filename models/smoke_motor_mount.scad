$fn = 96;
PRINT_ANCHOR_BBOX = [60, 40, 5];

plate_w = 60; plate_d = 40; plate_t = 5;
bore = 20; boss = 2;
hole_d = 3.2; hole_dx = 48; hole_dy = 28;
cb_d = 6; cb_depth = 2;

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
