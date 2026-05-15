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
  popcorn_kernel: {
    categoryId: "toys",
    blurb:
      "Cartoonish popcorn kernel. Smoke-testable glyph with a handful of dial-your-shape parameters.",
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
};
