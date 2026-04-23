// Static catalog joined onto filesystem-discovered models. Every .scad
// stem under models/ must have an entry here; listModels() throws on a
// missing stem rather than falling back to a 'misc' bucket. That keeps
// new models from quietly landing in the wrong shelf — adding a model
// means editing CATALOG as part of the same change.

export const MODEL_CATEGORIES = [
  { id: "storage", label: "Storage" },
  { id: "multiboard", label: "Multiboard" },
  { id: "toys", label: "Toys" },
] as const;

export type CategoryId = (typeof MODEL_CATEGORIES)[number]["id"];

export interface CatalogEntry {
  categoryId: CategoryId;
  blurb: string;
}

export const CATALOG: Record<string, CatalogEntry> = {
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
};
