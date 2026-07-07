// Unit tests for the native render service client (st-d32). The WIF token
// exchange is mocked (auth.test.ts covers its wiring); fetch is mocked so
// every network outcome — success, 5xx, timeout, refusal — is exercised
// without a live service. The invariant under test throughout: the client
// NEVER throws, because the export route's WASM fallback hangs off a plain
// ok:false check.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./auth", () => ({
  fetchGcpIdToken: vi.fn(async () => "gcp-id-token"),
}));

import { fetchGcpIdToken } from "./auth";
import {
  getRenderServiceConfig,
  renderViaService,
  resetRenderServiceConfigWarning,
  type RenderServiceConfig,
} from "./client";

const ENV_KEYS = [
  "RENDER_SERVICE_URL",
  "GCP_WORKLOAD_IDENTITY_PROVIDER",
  "GCP_RENDER_INVOKER_SA",
] as const;

const CONFIG: RenderServiceConfig = {
  url: "https://render.example.run.app",
  audience: "https://render.example.run.app",
  workloadIdentityProvider:
    "projects/123/locations/global/workloadIdentityPools/vercel/providers/vercel",
  serviceAccountEmail: "render-invoker@proj.iam.gserviceaccount.com",
};

function stlResponse(bytes: Uint8Array, headers: Record<string, string> = {}): Response {
  return new Response(new Uint8Array(bytes), {
    status: 200,
    headers: { "content-type": "application/sla", ...headers },
  });
}

beforeEach(() => {
  for (const k of ENV_KEYS) delete process.env[k];
  resetRenderServiceConfigWarning();
  vi.mocked(fetchGcpIdToken).mockClear();
  vi.mocked(fetchGcpIdToken).mockResolvedValue("gcp-id-token");
});

afterEach(() => {
  for (const k of ENV_KEYS) delete process.env[k];
  vi.unstubAllGlobals();
});

describe("getRenderServiceConfig", () => {
  it("is null when RENDER_SERVICE_URL is unset (feature off)", () => {
    expect(getRenderServiceConfig()).toBeNull();
  });

  it("is null (disabled, warned) when the WIF env is incomplete", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    process.env.RENDER_SERVICE_URL = CONFIG.url;
    // no provider / SA set
    expect(getRenderServiceConfig()).toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    // warn-once: a second read stays quiet
    expect(getRenderServiceConfig()).toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  it("is null (disabled, warned) when the URL is unparseable", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    process.env.RENDER_SERVICE_URL = "not a url";
    process.env.GCP_WORKLOAD_IDENTITY_PROVIDER = CONFIG.workloadIdentityProvider;
    process.env.GCP_RENDER_INVOKER_SA = CONFIG.serviceAccountEmail;
    expect(getRenderServiceConfig()).toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  it("parses a complete env, deriving the audience from the URL origin", () => {
    process.env.RENDER_SERVICE_URL = CONFIG.url + "/";
    process.env.GCP_WORKLOAD_IDENTITY_PROVIDER = CONFIG.workloadIdentityProvider;
    process.env.GCP_RENDER_INVOKER_SA = CONFIG.serviceAccountEmail;
    expect(getRenderServiceConfig()).toEqual({ ...CONFIG, url: CONFIG.url + "/" });
  });
});

describe("renderViaService", () => {
  it("POSTs model+params with a Bearer ID token and returns the STL bytes", async () => {
    const bytes = new Uint8Array([0x53, 0x54, 0x4c, 0x21]);
    const fetchMock = vi.fn(async () => stlResponse(bytes, { "x-render-ms": "6500" }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: { width: 40, mount_type: "opengrid" },
      vercelOidcToken: "vercel-oidc",
    });

    expect(result.ok).toBe(true);
    expect(Array.from(result.stl!)).toEqual(Array.from(bytes));
    expect(result.renderMs).toBe(6500);

    expect(fetchGcpIdToken).toHaveBeenCalledWith({
      vercelOidcToken: "vercel-oidc",
      workloadIdentityProvider: CONFIG.workloadIdentityProvider,
      serviceAccountEmail: CONFIG.serviceAccountEmail,
      audience: CONFIG.audience,
    });

    const [url, init] = fetchMock.mock.calls[0] as unknown as [URL, RequestInit];
    expect(String(url)).toBe("https://render.example.run.app/render");
    expect(init.method).toBe("POST");
    expect((init.headers as Record<string, string>).authorization).toBe(
      "Bearer gcp-id-token",
    );
    expect(JSON.parse(init.body as string)).toEqual({
      model: "models/foo.scad",
      params: { width: 40, mount_type: "opengrid" },
    });
  });

  it("fails soft without an OIDC token (never calls the service)", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: null,
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toMatch(/OIDC token/);
    expect(fetchMock).not.toHaveBeenCalled();
    expect(fetchGcpIdToken).not.toHaveBeenCalled();
  });

  it("fails soft when the WIF token exchange throws", async () => {
    vi.mocked(fetchGcpIdToken).mockRejectedValueOnce(new Error("STS said no"));
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: "vercel-oidc",
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toMatch(/WIF token exchange failed: STS said no/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("fails soft when fetch rejects (network/timeout)", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new DOMException("The operation timed out.", "TimeoutError");
    }));
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: "vercel-oidc",
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toMatch(/render service unreachable/);
  });

  it("fails soft on a non-200, surfacing the service's errorMessage", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response(JSON.stringify({ ok: false, errorMessage: "openscad exploded" }), {
        status: 500,
        headers: { "content-type": "application/json" },
      }),
    ));
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: "vercel-oidc",
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toBe("render service HTTP 500: openscad exploded");
  });

  it("fails soft on a non-200 with a non-JSON body", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      new Response("Service Unavailable", { status: 503 }),
    ));
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: "vercel-oidc",
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toBe("render service HTTP 503");
  });

  it("rejects an empty 200 body — empty bytes must never look like a model", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => stlResponse(new Uint8Array(0))));
    const result = await renderViaService({
      config: CONFIG,
      model: "models/foo.scad",
      params: {},
      vercelOidcToken: "vercel-oidc",
    });
    expect(result.ok).toBe(false);
    expect(result.errorMessage).toMatch(/empty body/);
  });
});
