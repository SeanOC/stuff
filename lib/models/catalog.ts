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
      "Wall cradle for a 51×84×7mm LED-strip remote. Open-front pocket with 45°-chamfered retaining lips and a thumb scoop, on a selectable back mount — a 2×3 grid of openGrid snaps on 28mm pitch or a Multiconnect slot backer for Multiboard rails (slides down onto wall connectors, weight seats into the slot domes). Prints mount-down, support-free; exports one STL per mount_type.",
  },
  led_remote_holder_55x124mm: {
    categoryId: "multiboard",
    blurb:
      "OpenGrid wall cradle for a 55×124×7.7mm LED-strip remote. Same design as the 51×84 twin with a selectable back mount — a 2×4 openGrid snap grid (default) or a Multiconnect slot backer for Multiboard rails; the plate is capped at 116mm so the remote stands ~10mm proud for easy grabbing. Exports one STL per mount_type.",
  },
  opengrid_bin: {
    categoryId: "multiboard",
    blurb:
      "Open-topped wall bin sized in 28mm grid units so it aligns with the tiles. Fused to the selected back mount — one directional openGrid snap per tile (strong nub up for the cantilever load) or a Multiconnect slot backer for Multiboard rails (slides down onto wall connectors, load seats into the slot domes). Full-height sides, 45° scoop front lip, rear floor fillet; prints mount-down, support-free. Exports one STL per mount_type.",
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
      "Saddle hanger for Disney-style ear headbands (Mickey/Minnie) — wall-mounts with double-sided tape or 3M Command strips, and the headbands drape over the saddle arch. Remix of a MakerWorld model by SpruceWayne (CC BY-NC-SA 4.0, non-commercial); hangerLength tunes how far the saddle projects off the wall. See the file header for attribution.",
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
  ego_powerhead_mount: {
    categoryId: "multiboard",
    blurb:
      "Ego Power+ powerhead wall holder converted from screw-mount to openGrid: the operator's holder mesh import()ed as-is, its four countersunk screw holes plugged solid, and eight directional openGrid snaps (strong nub up) fused to a grid-aligned back plate. Prints supportless snaps-down — snap the four breakaway ribs out of the shelf notches before first use. Hangs the powerhead by its shaft on the original fork and shelf bearing surfaces.",
  },
  ryobi_p2860_strap_saddle: {
    categoryId: "multiboard",
    blurb:
      "Shoulder saddle pair for hanging a Ryobi ONE+ P2860 backpack sprayer by its padded straps on an openGrid wall — print one left and one right. Crowned 42mm prong with a 55mm saddle dip and 12mm retention lip seats an 80mm strap exactly as it drapes on a shoulder; directional snaps put the strong nub up. Empty-sprayer duty (~7kg total), snaps-down zero-support print.",
  },
  ego_ea0820_edger_mount: {
    categoryId: "multiboard",
    blurb:
      "Ego MultiHead EA0820 edger attachment wall mount converted from screw-mount to openGrid: the operator's bracket mesh import()ed as-is, its four countersunk screw holes plugged solid, and ten directional openGrid snaps (strong nub up) fused to a grid-aligned extended back plate. Prints supportless snaps-down — snap the two breakaway ribs out of the tool slots before first use. Hangs the EA0820 edger head by its original slot bearing surfaces.",
  },
  littletikes_dream_machine_cartridge_holder: {
    categoryId: "toys",
    blurb:
      "Wall-mounted holder for Little Tikes Dream Machine cartridges and figures — an openGrid tray sized in whole 28mm cells that auto-fills with 51x14 cartridge slots (top) and rounded figure pockets (front). Pick a back-face mount: openGrid lite snaps (default), a blank flat back, or openConnect receivers — all on the same 28mm cell grid. The preview shows a compact 2x4-cell tile; scale the cell count up to 9x8 for the full-size holder.",
  },
  us_electrical_box_extender: {
    categoryId: "household",
    blurb:
      "US electrical box extension ring that builds out a 1-4 gang box flush with a thick wall. Ports a proven MakerWorld design: rounded rect_tube shell with per-gang screw posts on the standard US box hole spacing.",
  },
  apple_tv_4th_gen_holder: {
    categoryId: "multiboard",
    blurb:
      "OpenGrid wall cradle that stands a 4th-gen Apple TV HD (98x98x35mm) on edge, flat against the panel, so it protrudes only ~45mm — low enough to tuck behind a wall-mounted TV. Slide-in cradle: shelf on the plate's bottom edge, two side rails with 45deg retaining lips, open top. The port edge faces down, so plugs drop through the shelf's cable cutout; two back lands hold the device off the plate for a full-height air channel, vented through one big gabled plate window that doubles as the lightening cut. Selectable back mount: the default four corner-tile directional openGrid snaps on a 4x4-tile plate (strong nub up) leave that window open through to the panel, or a Multiconnect slot backer for Multiboard rails — its solid 6.5mm slab seats behind the plate, so the vent becomes a blind relief pocket backed by the mount (accepted by design 2026-08-17; the channel still breathes out the open cradle top). Exports one STL per mount_type. Load it at the bench (tilt the bottom edge in, rock the top back behind the lips) before snapping it to the panel. Prints STANDING on the plate's bottom edge — 9x less overhang than lying snaps-down, and no support scars on the panel-mating face; the only supports are under the four snaps.",
  },
  opengrid_snaps: {
    categoryId: "multiboard",
    blurb:
      "Ready-to-print openGrid snap connectors (28mm pitch). One STL per variant: lite/full depth x directional/bidirectional. Press straight into an openGrid board.",
  },
  multiconnect_connectors: {
    categoryId: "multiboard",
    blurb:
      "Ready-to-print Multiconnect (Multiboard) connectors that lock an accessory backer into a tile (25mm grid). One STL per variant: snap-regular (bidirectional click snap) or pushfit (press-in peg). Print one, press it in.",
  },
  kidscleancar_knob_cover: {
    categoryId: "toys",
    blurb:
      "Friction-fit childproof cover for the speed-adjust knob on a KidsCleanCar kids' ride-on. Slips over the 48.1mm lower flange and grips it with tunable internal crush ribs, spinning free over the knob so a toddler can't change the speed while a straight adult pull lifts it off. Original design; no vehicle modification, fully reversible.",
  },
  opengrid_multiconnect_adapter: {
    categoryId: "multiboard",
    blurb:
      "Cross-ecosystem wall adapter: clicks into an openGrid tile on the back (one directional snap per 28mm tile) and presents a Multiconnect receiver slot on the front (25mm pitch), so a Multiconnect-tabbed accessory hangs on an openGrid wall. Slot dome points down so weight seats the tab. Prints snaps-down, support-free; exports a single-slot (28mm) and a two-slot (56mm) STL.",
  },
};
