import { describe, expect, it } from "vitest";
import { listModels, loadModel, slugToStem, stemToSlug } from "./discover";

describe("stem/slug conversion", () => {
  it("round-trips underscore <-> dash", () => {
    expect(stemToSlug("cylindrical_holder_slot")).toBe("cylindrical-holder-slot");
    expect(slugToStem("cylindrical-holder-slot")).toBe("cylindrical_holder_slot");
  });

  it("leaves no-underscore stems untouched", () => {
    expect(stemToSlug("cube")).toBe("cube");
    expect(slugToStem("cube")).toBe("cube");
  });
});

describe("loadModel safety", () => {
  it("rejects slugs that resolve to traversal-y stems", async () => {
    expect(await loadModel("../etc/passwd")).toBeNull();
    expect(await loadModel("foo/bar")).toBeNull();
    expect(await loadModel(".hidden")).toBeNull();
  });

  it("returns null for non-existent models", async () => {
    expect(await loadModel("definitely-not-a-real-model")).toBeNull();
  });
});

describe("listModels", () => {
  it("includes the Phase 1 model and produces stable slugs", async () => {
    const models = await listModels();
    expect(models.length).toBeGreaterThan(0);
    const slugs = models.map((m) => m.slug);
    // Sorted alphabetically by stem; spot-check a known slug exists.
    expect(slugs).toContain("cylindrical-holder-slot");
    // Slug should be stable derivation, not random.
    expect(slugs).toEqual([...slugs].sort());
  });

  it("derives a non-empty title for every entry", async () => {
    const models = await listModels();
    for (const m of models) {
      expect(m.title.length).toBeGreaterThan(0);
    }
  });
});
