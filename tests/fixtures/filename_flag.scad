// Frozen test fixture for live-download naming (pst-fcjqj): one enum param
// carries the bare `filename` flag, so /api/export names the STL
// filename_flag-<style>.stl like scripts/export-all.py's baked grid.
// Library-free and tiny so the route test's wasm render stays fast.

$fn = 16;
PRINT_ANCHOR_BBOX = [10, 10, 4];

// === User-tunable parameters ===
style = "square"; // @param enum choices=square|round label="Style" filename
size  = 10;       // @param number min=5 max=20 step=1 label="Size (mm)"
// === Geometry ===

if (style == "round") cylinder(h = 4, d = size);
else translate([-size / 2, -size / 2, 0]) cube([size, size, 4]);
