// Frozen test fixture for the Phase 1/2 param-override silent-bug class.
// A plate where `width` and `thickness` visibly shift the printed bbox,
// so an unapplied override produces a wrong-size STL instead of a crash
// (the exact failure mode openscad-wasm-prebuilt caused by ignoring -D
// flags). Test asserts bbox differs between the default and an override.
//
// Intentionally minimal — no library includes, no CSG — so the render
// is cheap and the test runs fast. Do not import from other models or
// rename without updating bug-regression.spec.ts.

$fn = 32;
PRINT_ANCHOR_BBOX = [40, 20, 4];

// === User-tunable parameters ===
width     = 40;  // @param number min=10 max=200 step=1 label="Width (mm)"
depth     = 20;  // @param number min=10 max=200 step=1 label="Depth (mm)"
thickness = 4;   // @param number min=1  max=20  step=0.5 label="Thickness (mm)"
boss      = 3;   // @param number min=0  max=10  step=0.5 label="Boss height (mm)"
// === Geometry ===

translate([-width / 2, -depth / 2, 0])
    cube([width, depth, thickness]);
cylinder(h = thickness + boss, d = 8);
