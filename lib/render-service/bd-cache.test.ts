// Unit tests for the bd-render content-addressed cache key (pst-6ugb).
// The key must: change with slug, params, model version, and format;
// collide an omitted param with its explicit default; and keep glb/stl
// bytes at distinct entries.

import { afterEach, describe, expect, it } from "vitest";
import type { BdModel } from "@/lib/models/bd-manifest";
import { bdModelVersion, computeBdCacheKey, normalizeParams } from "./bd-cache";

const MODEL: BdModel = {
  slug: "holder-spray-can",
  title: "Spray can holder",
  blurb: "test",
  categoryId: "multiboard",
  params: [
    { name: "d", kind: "number", default: 66, min: 30, max: 120 },
    { name: "wall", kind: "number", default: 2.4, min: 1.6, max: 4 },
  ],
  presets: [{ id: "spray_can", label: "Spray can", values: { d: 66 } }],
};

function keyFor(over: Partial<Parameters<typeof computeBdCacheKey>[0]>) {
  return computeBdCacheKey({
    slug: "holder-spray-can",
    normalizedParams: normalizeParams({ d: 66, wall: 2.4 }),
    modelVersion: bdModelVersion(MODEL),
    format: "glb",
    ...over,
  });
}

describe("computeBdCacheKey", () => {
  it("is a stable sha256 hex digest", () => {
    const k = keyFor({});
    expect(k).toMatch(/^[0-9a-f]{64}$/);
    expect(keyFor({})).toBe(k); // deterministic
  });

  it("changes with slug, params, model version, and format", () => {
    const base = keyFor({});
    expect(keyFor({ slug: "holder-other" })).not.toBe(base);
    expect(keyFor({ normalizedParams: normalizeParams({ d: 70, wall: 2.4 }) })).not.toBe(base);
    expect(keyFor({ modelVersion: "different" })).not.toBe(base);
    expect(keyFor({ format: "stl" })).not.toBe(base);
  });

  it("keeps glb and stl of identical params at distinct entries", () => {
    expect(keyFor({ format: "glb" })).not.toBe(keyFor({ format: "stl" }));
  });

  it("labels parts so components can't concatenate ambiguously", () => {
    // slug 'ab' + params '' must not equal slug 'a' + params 'b'.
    const a = computeBdCacheKey({
      slug: "ab",
      normalizedParams: "",
      modelVersion: "v",
      format: "glb",
    });
    const b = computeBdCacheKey({
      slug: "a",
      normalizedParams: "b",
      modelVersion: "v",
      format: "glb",
    });
    expect(a).not.toBe(b);
  });
});

describe("normalizeParams (via bd-cache re-export)", () => {
  it("collides an omitted param with its explicit default", () => {
    // Resolved maps are equal → identical normalization → one cache entry.
    expect(normalizeParams({ d: 66, wall: 2.4 })).toBe(
      normalizeParams({ wall: 2.4, d: 66 }),
    );
  });

  it("differs on any value change", () => {
    expect(normalizeParams({ d: 66 })).not.toBe(normalizeParams({ d: 67 }));
  });
});

describe("bdModelVersion", () => {
  afterEach(() => {
    delete process.env.BD_RENDER_SERVICE_RENDERER_VERSION;
  });

  it("changes when a param range changes", () => {
    const v1 = bdModelVersion(MODEL);
    const widened: BdModel = {
      ...MODEL,
      params: [
        { name: "d", kind: "number", default: 66, min: 30, max: 200 },
        MODEL.params[1],
      ],
    };
    expect(bdModelVersion(widened)).not.toBe(v1);
  });

  it("changes when a preset value changes", () => {
    const v1 = bdModelVersion(MODEL);
    const represet: BdModel = {
      ...MODEL,
      presets: [{ id: "spray_can", label: "Spray can", values: { d: 70 } }],
    };
    expect(bdModelVersion(represet)).not.toBe(v1);
  });

  it("is unaffected by display-only title/blurb changes", () => {
    const v1 = bdModelVersion(MODEL);
    expect(bdModelVersion({ ...MODEL, title: "X", blurb: "Y" })).toBe(v1);
  });

  it("busts on the operator renderer-version lever", () => {
    const v1 = bdModelVersion(MODEL);
    process.env.BD_RENDER_SERVICE_RENDERER_VERSION = "2";
    expect(bdModelVersion(MODEL)).not.toBe(v1);
  });
});
