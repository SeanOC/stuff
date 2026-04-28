import fs from "node:fs/promises";
import path from "node:path";
import { afterAll, afterEach, describe, expect, it, vi } from "vitest";
import { ACCESSORIES } from "./catalog";
import {
  getAccessoriesForModel,
  getAccessoryBySlug,
  getModelsForAccessory,
  listAccessories,
} from "./discover";

describe("listAccessories", () => {
  it("returns the seed entry with a positive fileSize and download URL", async () => {
    const all = await listAccessories();
    const seed = all.find((a) => a.slug === "openconnect-flush-mid-coin");
    expect(seed).toBeDefined();
    expect(seed!.fileSize).toBeGreaterThan(0);
    expect(seed!.downloadUrl).toBe("/api/accessories/openconnect-flush-mid-coin");
    expect(seed!.stlPath).toBe("accessories/openconnect-flush-mid-coin.stl");
  });

  it("every catalog entry resolves to an STL on disk", async () => {
    // Acceptance check that complements the warn-and-skip behaviour in
    // listAccessories: a missing file would silently drop from the
    // returned list, so without this assertion an accidental rename
    // would ship a broken catalog. CI catches that here.
    const all = await listAccessories();
    expect(all).toHaveLength(ACCESSORIES.length);
  });

  it("every compatibleModels stem points at a real .scad file", async () => {
    // Renaming a model stem without updating the accessory catalog
    // would silently leave dangling references; this test makes that
    // change loud.
    const modelsDir = path.resolve(process.cwd(), "models");
    const stems = (await fs.readdir(modelsDir))
      .filter((f) => f.endsWith(".scad"))
      .map((f) => f.slice(0, -".scad".length));
    for (const entry of ACCESSORIES) {
      for (const stem of entry.compatibleModels) {
        expect(stems, `model stem for accessory "${entry.slug}"`).toContain(stem);
      }
    }
  });
});

describe("getAccessoryBySlug", () => {
  it("returns the seed entry by slug", async () => {
    const seed = await getAccessoryBySlug("openconnect-flush-mid-coin");
    expect(seed).not.toBeNull();
    expect(seed!.title).toMatch(/openconnect/i);
  });

  it("returns null for unknown slugs", async () => {
    expect(await getAccessoryBySlug("not-a-real-accessory")).toBeNull();
  });

  it("rejects traversal-y slugs without touching disk", async () => {
    expect(await getAccessoryBySlug("../etc/passwd")).toBeNull();
    expect(await getAccessoryBySlug("foo/bar")).toBeNull();
    expect(await getAccessoryBySlug(".hidden")).toBeNull();
  });
});

describe("getAccessoriesForModel", () => {
  it("returns the seed accessory for cylindrical_holder_slot", async () => {
    const accs = await getAccessoriesForModel("cylindrical_holder_slot");
    expect(accs.map((a) => a.slug)).toContain("openconnect-flush-mid-coin");
  });

  it("returns [] for a model with no compatible accessories", async () => {
    expect(await getAccessoriesForModel("nonexistent_model")).toEqual([]);
    // Spot-check a real model that has no accessories yet.
    expect(await getAccessoriesForModel("popcorn_kernel")).toEqual([]);
  });
});

describe("getModelsForAccessory", () => {
  it("returns the compatible model stems for the seed accessory", async () => {
    const stems = await getModelsForAccessory("openconnect-flush-mid-coin");
    expect(stems).toEqual(["cylindrical_holder_slot"]);
  });

  it("returns [] for an unknown accessory slug", async () => {
    expect(await getModelsForAccessory("not-a-real-accessory")).toEqual([]);
  });

  it("returns a fresh array (mutating it doesn't poison the catalog)", async () => {
    const first = await getModelsForAccessory("openconnect-flush-mid-coin");
    first.push("evil_injected_stem");
    const second = await getModelsForAccessory("openconnect-flush-mid-coin");
    expect(second).toEqual(["cylindrical_holder_slot"]);
  });
});

describe("listAccessories — missing-file handling", () => {
  // We can't easily delete the seed STL inside a unit test, so simulate
  // the "catalog entry but no file" state by stubbing fs.stat. The
  // assertion is that listAccessories warns and skips the entry rather
  // than throwing.
  const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

  afterEach(() => warnSpy.mockClear());
  afterAll(() => warnSpy.mockRestore());

  it("warns and skips an entry whose STL is missing", async () => {
    const statSpy = vi.spyOn(fs, "stat").mockImplementation(async () => {
      const err = new Error("ENOENT") as NodeJS.ErrnoException;
      err.code = "ENOENT";
      throw err;
    });
    try {
      const all = await listAccessories();
      expect(all).toEqual([]);
      expect(warnSpy).toHaveBeenCalled();
      const msg = String(warnSpy.mock.calls[0]?.[0] ?? "");
      expect(msg).toMatch(/missing STL/);
    } finally {
      statSpy.mockRestore();
    }
  });
});
