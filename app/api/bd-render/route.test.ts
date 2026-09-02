// Route-level tests for /api/bd-render (pst-6ugb). The bd-render service
// client and the manifest loader are mocked so the route's own logic —
// gating, format/shape/range validation, cache HIT/MISS, and the no-fallback
// 502 — is exercised without a live Cloud Run service or a committed model.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { BdModel } from "@/lib/models/bd-manifest";
import type { BdRenderResult } from "@/lib/render-service/bd-client";

// bd-render service client: mocked so every render outcome is scripted.
const bdClient = vi.hoisted(() => ({
  getBdRenderServiceConfig: vi.fn((): unknown => ({
    url: "https://bd.example.run.app",
    audience: "https://bd.example.run.app",
    workloadIdentityProvider: "projects/1/.../providers/vercel",
    serviceAccountEmail: "bd-invoker@proj.iam.gserviceaccount.com",
  })),
  renderBdViaService: vi.fn(),
}));
vi.mock("@/lib/render-service/bd-client", () => bdClient);

// Manifest loader: return one controlled model; keep bdModelsEnabled real
// (it reads BD_MODELS_ENABLED, which the tests set directly).
const MODEL: BdModel = {
  slug: "holder-spray-can",
  title: "Spray can holder",
  blurb: "test",
  categoryId: "multiboard",
  params: [
    { name: "d", kind: "number", default: 66, min: 30, max: 120 },
    { name: "count", kind: "integer", default: 2, min: 1, max: 4 },
    { name: "mode", kind: "enum", default: "a", choices: ["a", "b"] },
    // Multiconnect mount tunables (pst-c1qo) — the route must accept them.
    { name: "slot_count", kind: "integer", default: 1, min: 1, max: 3 },
    { name: "slot_travel", kind: "number", default: 28, min: 12, max: 45 },
    { name: "snap_notches", kind: "boolean", default: true },
    { name: "plate_margin", kind: "number", default: 3, min: 2, max: 6 },
  ],
  presets: [],
};
const manifest = vi.hoisted(() => ({ loadBdModel: vi.fn() }));
vi.mock("@/lib/models/bd-manifest", async (orig) => ({
  ...(await orig<typeof import("@/lib/models/bd-manifest")>()),
  loadBdModel: manifest.loadBdModel,
}));

// In-memory Vercel Blob, keyed by pathname (mirrors the content-addressed store).
const blobStore = new Map<string, Uint8Array>();
vi.mock("@vercel/blob", () => ({
  get: async (pathname: string) => {
    const buf = blobStore.get(pathname);
    if (!buf) return null;
    return { stream: new Response(new Uint8Array(buf)).body, blob: {}, headers: new Headers() };
  },
  put: async (pathname: string, body: Uint8Array) => {
    blobStore.set(pathname, new Uint8Array(body));
    return { url: `mock://${pathname}`, pathname };
  },
}));

import { POST } from "./route";

function post(bodyObj: unknown, query = ""): Request {
  return new Request(`http://localhost/api/bd-render${query}`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-vercel-oidc-token": "tok" },
    body: JSON.stringify(bodyObj),
  });
}

async function call(bodyObj: unknown, query = "") {
  const res = await POST(post(bodyObj, query) as never);
  const bytes = new Uint8Array(await res.arrayBuffer());
  let json: Record<string, unknown> | null = null;
  try {
    json = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    // binary (GLB/STL) body — not JSON
  }
  return { res, bytes, json };
}

function okResult(bytes = new Uint8Array([1, 2, 3])): BdRenderResult {
  return { ok: true, bytes, renderMs: 42 };
}

beforeEach(() => {
  blobStore.clear();
  process.env.BD_MODELS_ENABLED = "1";
  process.env.BLOB_READ_WRITE_TOKEN = "vercel_blob_rw_test";
  bdClient.getBdRenderServiceConfig.mockReturnValue({
    url: "https://bd.example.run.app",
    audience: "https://bd.example.run.app",
    workloadIdentityProvider: "projects/1/.../providers/vercel",
    serviceAccountEmail: "bd-invoker@proj.iam.gserviceaccount.com",
  });
  bdClient.renderBdViaService.mockResolvedValue(okResult());
  manifest.loadBdModel.mockResolvedValue(MODEL);
});

afterEach(() => {
  delete process.env.BD_MODELS_ENABLED;
  delete process.env.BLOB_READ_WRITE_TOKEN;
  vi.clearAllMocks();
});

describe("/api/bd-render gating", () => {
  it("503 {disabled:true} when the flag is off", async () => {
    delete process.env.BD_MODELS_ENABLED;
    const { res, json } = await call({ slug: "holder-spray-can", params: {} });
    expect(res.status).toBe(503);
    expect(json!).toMatchObject({ disabled: true });
    expect(bdClient.renderBdViaService).not.toHaveBeenCalled();
  });

  it("503 {disabled:true} when no service config", async () => {
    bdClient.getBdRenderServiceConfig.mockReturnValue(null);
    const { res, json } = await call({ slug: "holder-spray-can", params: {} });
    expect(res.status).toBe(503);
    expect(json!).toMatchObject({ disabled: true });
  });
});

describe("/api/bd-render validation", () => {
  it("400 on bad format", async () => {
    const { res } = await call({ slug: "holder-spray-can", params: {} }, "?format=obj");
    expect(res.status).toBe(400);
  });

  it("400 when slug is not a string", async () => {
    const { res } = await call({ params: {} });
    expect(res.status).toBe(400);
  });

  it("404 on unknown slug", async () => {
    manifest.loadBdModel.mockResolvedValue(null);
    const { res } = await call({ slug: "nope", params: {} });
    expect(res.status).toBe(404);
  });

  it("400 on unknown param", async () => {
    const { res, json } = await call({ slug: "holder-spray-can", params: { bogus: 1 } });
    expect(res.status).toBe(400);
    expect((json!).error).toContain("unknown param");
    expect(bdClient.renderBdViaService).not.toHaveBeenCalled();
  });

  it("400 on out-of-range number (pre-check, no round-trip)", async () => {
    const { res, json } = await call({ slug: "holder-spray-can", params: { d: 999 } });
    expect(res.status).toBe(400);
    expect((json!).error).toContain("above max");
    expect(bdClient.renderBdViaService).not.toHaveBeenCalled();
  });

  it("400 on below-min number", async () => {
    const { res, json } = await call({ slug: "holder-spray-can", params: { d: 1 } });
    expect(res.status).toBe(400);
    expect((json!).error).toContain("below min");
  });

  it("400 on enum value outside choices", async () => {
    const { res } = await call({ slug: "holder-spray-can", params: { mode: "z" } });
    expect(res.status).toBe(400);
  });

  it("accepts an in-range value", async () => {
    const { res } = await call({ slug: "holder-spray-can", params: { d: 70, count: 3 } });
    expect(res.status).toBe(200);
    expect(bdClient.renderBdViaService).toHaveBeenCalledTimes(1);
  });

  it("accepts the Multiconnect mount tunables and forwards them", async () => {
    const { res } = await call({
      slug: "holder-spray-can",
      params: { slot_count: 3, slot_travel: 45, snap_notches: false, plate_margin: 6 },
    });
    expect(res.status).toBe(200);
    expect(bdClient.renderBdViaService).toHaveBeenCalledTimes(1);
    const forwarded = bdClient.renderBdViaService.mock.calls[0][0].params;
    expect(forwarded).toMatchObject({
      slot_count: 3,
      slot_travel: 45,
      snap_notches: false,
      plate_margin: 6,
    });
  });

  it('coerces "true"/"false" strings for a boolean mount param', async () => {
    const { res } = await call({ slug: "holder-spray-can", params: { snap_notches: "false" } });
    expect(res.status).toBe(200);
    expect(bdClient.renderBdViaService.mock.calls[0][0].params.snap_notches).toBe(false);
  });

  it("400 on out-of-range slot_travel (below the library-derived floor)", async () => {
    const { res, json } = await call({ slug: "holder-spray-can", params: { slot_travel: 5 } });
    expect(res.status).toBe(400);
    expect((json!).error).toContain("below min");
    expect(bdClient.renderBdViaService).not.toHaveBeenCalled();
  });

  it("400 on out-of-range slot_count", async () => {
    const { res, json } = await call({ slug: "holder-spray-can", params: { slot_count: 4 } });
    expect(res.status).toBe(400);
    expect((json!).error).toContain("above max");
  });
});

describe("/api/bd-render render + cache", () => {
  it("serves GLB by default and STL as a download on ?format=stl", async () => {
    const glb = await call({ slug: "holder-spray-can", params: { d: 70 } });
    expect(glb.res.status).toBe(200);
    expect(glb.res.headers.get("content-type")).toBe("model/gltf-binary");
    expect(glb.res.headers.get("content-disposition")).toBeNull();

    const stl = await call({ slug: "holder-spray-can", params: { d: 70 } }, "?format=stl");
    expect(stl.res.status).toBe(200);
    expect(stl.res.headers.get("content-type")).toBe("application/sla");
    expect(stl.res.headers.get("content-disposition")).toContain(".stl");
    // glb was sent with format glb, stl with format stl.
    expect(bdClient.renderBdViaService).toHaveBeenLastCalledWith(
      expect.objectContaining({ format: "stl" }),
    );
  });

  it("MISS then HIT: identical request serves from cache, no second render", async () => {
    const first = await call({ slug: "holder-spray-can", params: { d: 70 } });
    expect(first.res.headers.get("x-cache")).toBe("MISS");
    expect(first.res.headers.get("cache-control")).toBe("no-store");
    expect(first.res.headers.get("x-render-ms")).toBe("42");

    const second = await call({ slug: "holder-spray-can", params: { d: 70 } });
    expect(second.res.headers.get("x-cache")).toBe("HIT");
    expect(second.res.headers.get("cache-control")).toContain("immutable");
    expect(Array.from(second.bytes)).toEqual(Array.from(first.bytes));
    expect(bdClient.renderBdViaService).toHaveBeenCalledTimes(1); // only the MISS rendered
  });

  it("omitted vs explicit-default collide to one cache entry (HIT)", async () => {
    // d default is 66; {} and {d:66} resolve to the same normalized params.
    const a = await call({ slug: "holder-spray-can", params: {} });
    expect(a.res.headers.get("x-cache")).toBe("MISS");
    const b = await call({ slug: "holder-spray-can", params: { d: 66 } });
    expect(b.res.headers.get("x-cache")).toBe("HIT");
    expect(bdClient.renderBdViaService).toHaveBeenCalledTimes(1);
  });

  it("glb and stl do not share a cache entry", async () => {
    await call({ slug: "holder-spray-can", params: { d: 70 } });
    const stl = await call({ slug: "holder-spray-can", params: { d: 70 } }, "?format=stl");
    expect(stl.res.headers.get("x-cache")).toBe("MISS"); // distinct key
    expect(bdClient.renderBdViaService).toHaveBeenCalledTimes(2);
  });

  it("502 structured error on service failure — NO fallback", async () => {
    bdClient.renderBdViaService.mockResolvedValue({
      ok: false,
      errorMessage: "OCP build failed",
    });
    const { res, json } = await call({ slug: "holder-spray-can", params: { d: 70 } });
    expect(res.status).toBe(502);
    expect((json!).upstream).toContain("OCP build failed");
    expect(blobStore.size).toBe(0); // failed render never cached
  });

  it("renders live (no cache) when Blob token is absent", async () => {
    delete process.env.BLOB_READ_WRITE_TOKEN;
    const { res } = await call({ slug: "holder-spray-can", params: { d: 70 } });
    expect(res.status).toBe(200);
    expect(res.headers.get("x-cache")).toBeNull();
  });
});
