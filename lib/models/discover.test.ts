import { describe, expect, it } from "vitest";
import { listModels, loadModel, slugToStem, stemToSlug } from "./discover";

describe("stem/slug conversion", () => {
  it("round-trips underscore <-> dash", () => {
    expect(stemToSlug("cylinder_holder_46mm_slot")).toBe("cylinder-holder-46mm-slot");
    expect(slugToStem("cylinder-holder-46mm-slot")).toBe("cylinder_holder_46mm_slot");
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
    // Sorted alphabetically by stem; spot-check the Phase 1 slug exists.
    expect(slugs).toContain("cylinder-holder-46mm-slot");
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
