// Static catalog joined onto filesystem-discovered models. Every .scad
// stem under models/ must have an entry here; listModels() throws on a
// missing stem rather than falling back to a 'misc' bucket. That keeps
// new models from quietly landing in the wrong shelf — adding a model
// means editing CATALOG as part of the same change.

export const MODEL_CATEGORIES = [
  { id: "storage", label: "Storage" },
  { id: "multiboard", label: "Multiboard" },
  { id: "toys", label: "Toys" },
  { id: "household", label: "Household" },
] as const;

export type CategoryId = (typeof MODEL_CATEGORIES)[number]["id"];

export interface CatalogEntry {
  categoryId: CategoryId;
  blurb: string;
}

export const CATALOG: Record<string, CatalogEntry> = {
  aquor_bib_drip_deflector: {
    categoryId: "household",
    blurb:
      "Under-bib drip deflector for Aquor hose bibs. VHB-mounts to the face-plate underside and kicks freeze-drain water outward, clear of the wall.",
  },
  cylindrical_holder_slot: {
    categoryId: "multiboard",
    blurb:
      "Open-front C-ring cradle with a Multiboard snap-slot backer. Takes any cylinder; the ring, wall, and slot region all flex on sliders.",
  },
  ego_lb6500_blower_mount: {
    categoryId: "multiboard",
    blurb:
      "Ego LB6500 leaf-blower wall bracket converted from screw-mount to a wall grid: a native parametric remodel of the original bracket (bearing surfaces held to <1mm of the source mesh) fused to the selected back mount — a 5-slot Multiconnect backer (slides down onto wall connectors, load seats into the slot domes) or 8 directional openGrid snaps with the strong nub up. Exports one STL per mount_type.",
  },
  led_remote_holder_51x84mm: {
    categoryId: "multiboard",
    blurb:
      "OpenGrid wall cradle for a 51×84×7mm LED-strip remote. Open-front pocket with 45°-chamfered retaining lips, thumb scoop, and a 2×3 grid of openGrid snaps on 28mm pitch. Prints snaps-down, support-free.",
  },
  led_remote_holder_55x124mm: {
    categoryId: "multiboard",
    blurb:
      "OpenGrid wall cradle for a 55×124×7.7mm LED-strip remote. Same design as the 51×84 twin with a 2×4 snap grid; the plate is capped at 116mm so the remote stands ~10mm proud for easy grabbing.",
  },
  opengrid_bin: {
    categoryId: "multiboard",
    blurb:
      "Open-topped wall bin for vertically-mounted openGrid panels, sized in 28mm grid units so it aligns with the tiles. One directional snap per tile (strong nub up for the cantilever load), full-height sides, 45° scoop front lip, and a rear floor fillet. Prints snaps-down, support-free.",
  },
  opengrid_panel_aligner: {
    categoryId: "multiboard",
    blurb:
      "Handheld alignment tool for installing openGrid panels: a stiff plate with a 2×2 array of openGrid snaps on 28mm pitch on one face and a domed grip knob on the other. Prints snaps-down with zero supports — the knob's cylinder-plus-dome profile has no overhang anywhere.",
  },
  popcorn_kernel: {
    categoryId: "toys",
    blurb:
      "Cartoonish popcorn kernel. Smoke-testable glyph with a handful of dial-your-shape parameters.",
  },
  lcd_stylus_75mm: {
    categoryId: "toys",
    blurb:
      "Rounded bullet stylus for kids' pressure-sensitive LCD drawing pads. ~2 mm dome tip, no hard edges, prints tip-up with no supports.",
  },
  lcd_stylus_hex_8mm: {
    categoryId: "toys",
    blurb:
      "Hex-profile stylus for kids' pressure-sensitive LCD drawing pads. Pencil-style anti-roll hexagon body with every edge filleted, ~2 mm dome tip, prints lying flat on a hex face with a built-in breakaway support fin under the tip.",
  },
  spraycan_carrier_6x50mm: {
    categoryId: "storage",
    blurb:
      "Six-cell tote for 50 mm spray cans. Drainage base plate, semicircular carry handle, kid-safe filleted edges.",
  },
  gridfinity_bin: {
    categoryId: "storage",
    blurb:
      "Parametric Gridfinity bin: pick a footprint, height, compartments, and base options. Snaps onto any standard 42mm Gridfinity baseplate.",
  },
  disney_ear_hanger: {
    categoryId: "household",
    blurb:
      "Vendored MakerWorld Disney ear hanger — wall-mount clip for Mickey/Minnie ear headbands. Original by an upstream MakerWorld author; see the file header for attribution.",
  },
  goblu_filter_holder_3x90mm: {
    categoryId: "household",
    blurb:
      "Side-mount holder for the goBlu 3-cylinder RV water filter assembly. Three flush-touching pods cradle 90mm filter housings; flat back face VHB-mounts to the RV wall.",
  },
  blu_flow_meter_mount_80mm: {
    categoryId: "household",
    blurb:
      "Captive bench mount for a Blu Technology digital flow meter (27mm × 80mm pipe). Two split-saddle pairs clamp the bare bands at each end of the meter; the middle 44mm gap leaves the LCD display saddle free. 4× M3 SHCS into heat-set inserts.",
  },
  blu_black_tank_valve_mount: {
    categoryId: "household",
    blurb:
      "Captive bench mount for a Blu Technology 3-way black-tank flush valve. Asymmetric saddles clamp the two inner fittings (31.5mm left, 29.25mm right) across a 37mm gap; vertical exclusion cylinder carves cap clearance for the T-handle's 90° swing. 4× M3 SHCS into heat-set inserts.",
  },
  rv_ceiling_ap_adapter_235mm: {
    categoryId: "household",
    blurb:
      "Adapter plate that covers a 235mm (9.25\") RV ceiling speaker cutout and mounts a WiFi access point in its place. Self-centering recessed cup nests up into the hole, 270mm one-piece flange (H2S bed) screws to the ceiling with 6 countersunk #6 screws, and a 100mm boss carries 4× M3 heat-set inserts on an 82.16mm bolt circle for the AP bracket, plus off-center arc-slot cable pass-throughs on the insert axes that line up with the bracket's offset wiring openings (its center hub is solid). Prints room-face-down with zero supports.",
  },
  blutech_water_softener_foot: {
    categoryId: "household",
    blurb:
      "Floor foot for an 8\" × 17\" BluTech RV water softener (~20 lbs full). Open-bottom ring cradle grips the cylinder bottom laterally at 85mm — cylinder drops through and rests on the RV floor, lifts straight up for maintenance. Six radial gussets transfer load into a continuous flat VHB-bearing annular flange; scupper notches at the base drain water laterally without breaching the bond face.",
  },
};
