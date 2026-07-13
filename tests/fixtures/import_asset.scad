// Frozen test fixture for the import()-asset download pipeline
// (st-zph class, pinned per pst-3m2 / GT st-0t8). A binary STL cube
// ([0,20]^3, tests/fixtures/import_asset_cube.stl) is import()ed and
// unioned with a native cuboid that overlaps it and extends past it in
// +X. OpenSCAD treats a missing import() as a WARNING, so if the
// export route ever stops delivering binary assets to the wasm FS the
// render would "succeed" with the mesh silently absent — the union
// then loses the imported half and the printed bbox visibly shrinks
// from 35 x 20 x 20 to 20 x 10 x 10 (and renderToStl's missingAssets
// hard-fail should have 500'd long before that). Test asserts the
// full-union bbox, watertightness, and a single component.
//
// Intentionally minimal — one tiny binary mesh + one primitive — so
// the render is cheap and the test runs fast. Do not rename this file
// or the .stl without updating stl-download.spec.ts.

PRINT_ANCHOR_BBOX = [35, 20, 20];

// === User-tunable parameters ===
reach = 15; // @param number min=5 max=50 step=1 label="Native cuboid reach past the mesh (mm)"
// === Geometry ===

import("import_asset_cube.stl", convexity = 2);
// Overlaps the cube's +X half so the union welds into one solid, and
// runs `reach` past its x=20 face — the imported mesh alone can't
// produce x > 20, and the cuboid alone can't produce the 20mm z span.
translate([10, 5, 5]) cube([10 + reach, 10, 10]);
