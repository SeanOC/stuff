// Loader tests for the build123d manifest ingestion (pst-dsiq).
// The committed manifest is the real fixture — its schema is pinned by
// the emitter's own validator (build123d/tests/test_manifest.py) and by
// CI's freshness gate, so a malformed-file test would be drift-prone;
// instead we assert the real file parses into a valid BdManifest.

import { describe, expect, it } from "vitest";
import { bdModelsEnabled, loadBdManifest, loadBdModel } from "./bd-manifest";

describe("loadBdManifest", () => {
  it("parses the committed manifest into the app contract", async () => {
    const manifest = await loadBdManifest();
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.models.length).toBeGreaterThanOrEqual(2);
    const slugs = new Set<string>();
    for (const model of manifest.models) {
      expect(model.slug).toMatch(/^[A-Za-z0-9-]+$/);
      expect(slugs.has(model.slug)).toBe(false);
      slugs.add(model.slug);
      expect(model.title).toBeTruthy();
      expect(model.blurb).toBeTruthy();
      expect(model.categoryId).toBeTruthy();
      for (const preset of model.presets) {
        for (const name of Object.keys(preset.values)) {
          expect(
            model.params.some((p) => p.name === name),
            `preset ${preset.id}.${name} references a declared param`,
          ).toBe(true);
        }
      }
    }
  });
});

describe("loadBdModel", () => {
  it("returns the manifest entry for a known slug", async () => {
    const model = await loadBdModel("holder-spray-can");
    expect(model).not.toBeNull();
    expect(model!.slug).toBe("holder-spray-can");
    expect(model!.presets.length).toBeGreaterThanOrEqual(1);
  });

  it("returns null for an unknown slug", async () => {
    expect(await loadBdModel("no-such-model")).toBeNull();
  });
});

describe("bdModelsEnabled", () => {
  it("is off by default and on only for the literal '1'", () => {
    delete process.env.BD_MODELS_ENABLED;
    expect(bdModelsEnabled()).toBe(false);
    process.env.BD_MODELS_ENABLED = "1";
    expect(bdModelsEnabled()).toBe(true);
    process.env.BD_MODELS_ENABLED = "yes";
    expect(bdModelsEnabled()).toBe(false);
    process.env.BD_MODELS_ENABLED = "0";
    expect(bdModelsEnabled()).toBe(false);
    delete process.env.BD_MODELS_ENABLED;
  });
});
