import { afterEach, describe, expect, it } from "vitest";
import { deriveTitle, listModels, listBdModels, loadModel, slugToStem, stemToSlug } from "./discover";
import { bdModelsEnabled } from "./bd-manifest";

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

describe("deriveTitle", () => {
  it("returns the first prose comment line", () => {
    const src = "// Hello world\nx = 1;\n";
    expect(deriveTitle(src, "fallback")).toBe("Hello world");
  });

  it("skips the SPDX + Copyright block so the prose line wins", () => {
    // Regression guard for st-1hh. Before the fix, the first //
    // line (`SPDX-License-Identifier: ...`) was returned verbatim
    // and the real title sat three lines below.
    const src = [
      "// SPDX-License-Identifier: CC-BY-NC-SA-4.0",
      "// Copyright (c) 2026 Sean O'Connor",
      "//",
      "// Multiboard-mounted holder for a cylindrical item",
      "// Additional prose here.",
      "",
      "x = 1;",
    ].join("\n");
    expect(deriveTitle(src, "fallback")).toBe(
      "Multiboard-mounted holder for a cylindrical item",
    );
  });

  it("falls back to the stem when no leading comment exists", () => {
    expect(deriveTitle("x = 1;\n", "popcorn_kernel")).toBe("popcorn kernel");
  });

  it("trims a trailing em/en/hyphen dash from the title", () => {
    expect(deriveTitle("// Cradle —\n", "fallback")).toBe("Cradle");
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

  it("joins catalog fields onto every entry", async () => {
    const models = await listModels();
    for (const m of models) {
      expect(m.categoryId, `categoryId for ${m.stem}`).toBeTruthy();
      expect(m.blurb.length, `blurb for ${m.stem}`).toBeGreaterThan(0);
    }
    const spraycan = models.find((m) => m.stem === "spraycan_carrier_6x50mm");
    expect(spraycan?.categoryId).toBe("storage");
  });
});

describe("build123d discovery (pst-dsiq)", () => {
  afterEach(() => {
    delete process.env.BD_MODELS_ENABLED;
  });

  it("listBdModels() merges manifest models into ModelEntry shape", async () => {
    const models = await listBdModels();
    expect(models.length).toBeGreaterThanOrEqual(2);
    const sprayCan = models.find((m) => m.slug === "holder-spray-can");
    expect(sprayCan, "manifest's holder-spray-can is listed").toBeDefined();
    expect(sprayCan?.engine).toBe("build123d");
    expect(sprayCan?.stem).toBe("holder_spray_can");
    expect(sprayCan?.modelPath).toBe("build123d/manifest.json");
    expect(sprayCan?.title).toBe("Spray can holder");
    expect(sprayCan?.paramCount).toBeGreaterThan(0);
    expect(sprayCan?.categoryId).toBe("multiboard");
    expect(sprayCan?.blurb.length).toBeGreaterThan(0);
    expect(sprayCan?.annotated).toBe(true);
  });

  it("listModels() excludes BD models while BD_MODELS_ENABLED is off (default)", async () => {
    delete process.env.BD_MODELS_ENABLED;
    expect(bdModelsEnabled()).toBe(false);
    const models = await listModels();
    expect(models.some((m) => m.engine === "build123d")).toBe(false);
    // SCAD side is untouched by the flag.
    expect(models.every((m) => m.engine === "scad")).toBe(true);
    expect(models.map((m) => m.slug)).toContain("cylindrical-holder-slot");
  });

  it("listModels() merges BD models when BD_MODELS_ENABLED=1, sorted by slug", async () => {
    process.env.BD_MODELS_ENABLED = "1";
    const models = await listModels();
    const bd = models.filter((m) => m.engine === "build123d");
    expect(bd.length).toBeGreaterThanOrEqual(2);
    const slugs = models.map((m) => m.slug);
    expect(slugs).toEqual([...slugs].sort((a, b) => a.localeCompare(b)));
    // BD cards must not collide with SCAD slugs.
    const scadSlugs = new Set(models.filter((m) => m.engine === "scad").map((m) => m.slug));
    for (const m of bd) {
      expect(scadSlugs.has(m.slug), `slug collision: ${m.slug}`).toBe(false);
    }
  });

  it("flag must be exactly '1' to enable (not truthy strings)", async () => {
    process.env.BD_MODELS_ENABLED = "true";
    const models = await listModels();
    expect(models.some((m) => m.engine === "build123d")).toBe(false);
  });

  it("loadModel() still refuses BD slugs until P1c (no detail routing)", async () => {
    const bd = await listBdModels();
    for (const m of bd) {
      expect(await loadModel(m.slug), `${m.slug} has no detail route yet`).toBeNull();
    }
  });
});
