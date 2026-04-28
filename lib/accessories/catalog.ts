// Static catalog of accessory STLs surfaced on model detail pages.
// Accessories are external static STL files (not parametric stuff
// models) with an M:N "compatible with" relation to models. Each entry
// here points at a file under `accessories/<slug>.stl` and lists the
// model stems it pairs with.
//
// Why TypeScript and not JSON: when a model stem gets renamed,
// `compatibleModels[]` references should fail typecheck-like via the
// integration test (lib/accessories/discover.test.ts) that asserts
// every listed stem resolves to a real model. Keeping this in TS also
// lets us reach for typed enums later without a format migration.

export interface AccessoryCatalogEntry {
  /** URL-safe slug; also the STL filename stem under accessories/. */
  slug: string;
  /** Display title shown on the model detail page. */
  title: string;
  /** One-line description rendered under the title. */
  blurb: string;
  /** Repo-relative path to the STL on disk. */
  stlPath: string;
  /**
   * Model stems (NOT slugs) this accessory pairs with. Stems are the
   * `.scad` filename without extension, e.g. "cylindrical_holder_slot".
   */
  compatibleModels: string[];
  /** Optional source / designer / license attribution. */
  attribution?: string;
}

export const ACCESSORIES: AccessoryCatalogEntry[] = [
  {
    slug: "openconnect-flush-mid-coin",
    title: "Openconnect Flush Mid Coin",
    blurb:
      "Mounts cylindrical holders to a Multiboard via the openconnect modular system.",
    stlPath: "accessories/openconnect-flush-mid-coin.stl",
    compatibleModels: ["cylindrical_holder_slot"],
  },
];
