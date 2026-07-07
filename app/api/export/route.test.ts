// Route-level integration for the export cache (st-uqk). Drives the real
// POST handler against a real wasm render of a tiny, library-free fixture,
// with @vercel/blob replaced by an in-memory store. Proves the end-to-end
// hit/miss behaviour the unit tests only cover at the key-composition layer.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Native render service client (st-d32): mocked so the native path can be
// driven without a Cloud Run service or WIF infra. Defaults to disabled
// (null config) so the pre-existing tests keep exercising today's
// flag-unset WASM-only behavior unchanged.
const renderService = vi.hoisted(() => ({
  getRenderServiceConfig: vi.fn((): unknown => null),
  renderViaService: vi.fn(),
}));
vi.mock("@/lib/render-service/client", () => renderService);

// In-memory stand-in for Vercel Blob. get/put are keyed by pathname, so this
// mirrors the content-addressed store the route relies on.
const blobStore = new Map<string, Uint8Array>();
vi.mock("@vercel/blob", () => ({
  get: async (pathname: string) => {
    const buf = blobStore.get(pathname);
    if (!buf) return null;
    const body = new Uint8Array(buf); // fresh ArrayBuffer-backed copy
    return { stream: new Response(body).body, blob: {}, headers: new Headers() };
  },
  put: async (pathname: string, body: Uint8Array) => {
    blobStore.set(pathname, new Uint8Array(body));
    return { url: `mock://${pathname}`, pathname };
  },
}));

import { POST } from "./route";

const MODEL = "tests/fixtures/bug_regression.scad";

function post(params: Record<string, unknown>): Request {
  return new Request("http://localhost/api/export", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model: MODEL, params }),
  });
}

async function callPost(params: Record<string, unknown>) {
  // POST only uses Request.json(); a plain Request satisfies it.
  const res = await POST(post(params) as never);
  const bytes = new Uint8Array(await res.arrayBuffer());
  return { res, bytes };
}

describe("/api/export cache (route integration)", () => {
  beforeEach(() => {
    blobStore.clear();
    process.env.BLOB_READ_WRITE_TOKEN = "vercel_blob_rw_test";
  });

  it("MISS then HIT: second identical request is byte-identical and immutable", async () => {
    const first = await callPost({ width: 55 });
    expect(first.res.status).toBe(200);
    expect(first.res.headers.get("x-cache")).toBe("MISS");
    expect(first.res.headers.get("cache-control")).toBe("no-store");
    expect(first.bytes.byteLength).toBeGreaterThan(0);

    const second = await callPost({ width: 55 });
    expect(second.res.status).toBe(200);
    expect(second.res.headers.get("x-cache")).toBe("HIT");
    expect(second.res.headers.get("cache-control")).toContain("immutable");
    expect(Array.from(second.bytes)).toEqual(Array.from(first.bytes));

    // One successful render → exactly one stored object.
    expect(blobStore.size).toBe(1);
  }, 30_000);

  it("omitted-vs-explicit-default collide to the same cache entry (HIT)", async () => {
    // bug_regression.scad declares width default 40. Rendering with {} then
    // {width:40} must hit the same key.
    const a = await callPost({});
    expect(a.res.headers.get("x-cache")).toBe("MISS");
    const b = await callPost({ width: 40 });
    expect(b.res.headers.get("x-cache")).toBe("HIT");
    expect(blobStore.size).toBe(1);
  }, 30_000);

  it("changing a param value forces a fresh render (MISS)", async () => {
    await callPost({ width: 40 });
    const changed = await callPost({ width: 120 });
    expect(changed.res.headers.get("x-cache")).toBe("MISS");
    expect(blobStore.size).toBe(2);
  }, 30_000);

  it("caching disabled (no token) → always live render, nothing stored", async () => {
    delete process.env.BLOB_READ_WRITE_TOKEN;
    const { res } = await callPost({ width: 40 });
    expect(res.status).toBe(200);
    // No x-cache header at all when the store is absent.
    expect(res.headers.get("x-cache")).toBeNull();
    expect(res.headers.get("cache-control")).toBe("no-store");
    expect(blobStore.size).toBe(0);
  }, 30_000);

  it("flag unset → x-renderer never appears (today's header set exactly)", async () => {
    const miss = await callPost({ width: 40 });
    expect(miss.res.headers.get("x-renderer")).toBeNull();
    const hit = await callPost({ width: 40 });
    expect(hit.res.headers.get("x-cache")).toBe("HIT");
    expect(hit.res.headers.get("x-renderer")).toBeNull();
  }, 30_000);
});

// st-d32: /api/export miss-path via the native render service, with WASM
// fallback and native/WASM cache-key separation. The service client is
// mocked (top of file); the WASM fallback renders are real.
describe("/api/export native render service path (st-d32)", () => {
  const CONFIG = {
    url: "https://render.example.run.app",
    audience: "https://render.example.run.app",
    workloadIdentityProvider:
      "projects/123/locations/global/workloadIdentityPools/vercel/providers/vercel",
    serviceAccountEmail: "render-invoker@proj.iam.gserviceaccount.com",
  };
  // Not a real STL — the route treats service bytes as opaque (the service
  // already enforces render correctness before returning 200).
  const NATIVE_BYTES = new Uint8Array([0x6e, 0x61, 0x74, 0x69, 0x76, 0x65]);

  beforeEach(() => {
    blobStore.clear();
    process.env.BLOB_READ_WRITE_TOKEN = "vercel_blob_rw_test";
    process.env.VERCEL_OIDC_TOKEN = "test-vercel-oidc";
    renderService.getRenderServiceConfig.mockReturnValue(CONFIG);
    renderService.renderViaService.mockReset();
  });

  afterEach(() => {
    renderService.getRenderServiceConfig.mockReturnValue(null);
    delete process.env.VERCEL_OIDC_TOKEN;
  });

  it("MISS renders via the service, caches, then HITs without re-calling it", async () => {
    renderService.renderViaService.mockResolvedValue({
      ok: true,
      stl: NATIVE_BYTES,
      renderMs: 6500,
    });

    const first = await callPost({ width: 55 });
    expect(first.res.status).toBe(200);
    expect(first.res.headers.get("x-cache")).toBe("MISS");
    expect(first.res.headers.get("x-renderer")).toBe("native");
    expect(first.res.headers.get("x-render-ms")).toBe("6500");
    expect(Array.from(first.bytes)).toEqual(Array.from(NATIVE_BYTES));
    expect(blobStore.size).toBe(1);

    // The service got the resolved param set (defaults filled) and this
    // request's OIDC token.
    expect(renderService.renderViaService).toHaveBeenCalledOnce();
    const call = renderService.renderViaService.mock.calls[0][0];
    expect(call.model).toBe(MODEL);
    expect(call.params).toEqual({ width: 55, depth: 20, thickness: 4, boss: 3 });
    expect(call.vercelOidcToken).toBe("test-vercel-oidc");

    const second = await callPost({ width: 55 });
    expect(second.res.headers.get("x-cache")).toBe("HIT");
    expect(second.res.headers.get("x-renderer")).toBe("native");
    expect(Array.from(second.bytes)).toEqual(Array.from(NATIVE_BYTES));
    expect(renderService.renderViaService).toHaveBeenCalledOnce();
  });

  it("native and WASM renders of identical content never share a cache entry", async () => {
    renderService.renderViaService.mockResolvedValue({ ok: true, stl: NATIVE_BYTES });
    await callPost({ width: 40 });
    expect(blobStore.size).toBe(1);

    // Same request with the feature off → the WASM key misses, a real WASM
    // render runs, and a SECOND entry appears (distinct rendererVersion).
    renderService.getRenderServiceConfig.mockReturnValue(null);
    const wasm = await callPost({ width: 40 });
    expect(wasm.res.headers.get("x-cache")).toBe("MISS");
    expect(blobStore.size).toBe(2);
  }, 30_000);

  it("service failure falls back to a real WASM render, cached under the WASM key", async () => {
    renderService.renderViaService.mockResolvedValue({
      ok: false,
      errorMessage: "render service HTTP 503",
    });

    const first = await callPost({ width: 40 });
    expect(first.res.status).toBe(200);
    expect(first.res.headers.get("x-cache")).toBe("MISS");
    expect(first.res.headers.get("x-renderer")).toBe("wasm");
    expect(first.bytes.byteLength).toBeGreaterThan(0);
    expect(blobStore.size).toBe(1);

    // Still failing: native key still misses, but the second-chance WASM
    // lookup HITs — no second render, no second entry.
    const second = await callPost({ width: 40 });
    expect(second.res.headers.get("x-cache")).toBe("HIT");
    expect(second.res.headers.get("x-renderer")).toBe("wasm");
    expect(Array.from(second.bytes)).toEqual(Array.from(first.bytes));
    expect(blobStore.size).toBe(1);
    expect(renderService.renderViaService).toHaveBeenCalledTimes(2);
  }, 60_000);

  it("no cache store: a service render still serves, with no x-cache signal", async () => {
    delete process.env.BLOB_READ_WRITE_TOKEN;
    renderService.renderViaService.mockResolvedValue({ ok: true, stl: NATIVE_BYTES });
    const { res, bytes } = await callPost({ width: 40 });
    expect(res.status).toBe(200);
    expect(res.headers.get("x-cache")).toBeNull();
    expect(res.headers.get("x-renderer")).toBe("native");
    expect(Array.from(bytes)).toEqual(Array.from(NATIVE_BYTES));
    expect(blobStore.size).toBe(0);
  });
});
