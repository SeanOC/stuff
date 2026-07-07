// Route-level integration for the export cache (st-uqk). Drives the real
// POST handler against a real wasm render of a tiny, library-free fixture,
// with @vercel/blob replaced by an in-memory store. Proves the end-to-end
// hit/miss behaviour the unit tests only cover at the key-composition layer.

import { beforeEach, describe, expect, it, vi } from "vitest";

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
});
