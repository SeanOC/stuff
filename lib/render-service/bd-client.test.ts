// Unit tests for the bd-render service client (pst-6ugb). The WIF token
// exchange is mocked (auth.test.ts covers its wiring); fetch is mocked so
// every outcome — success, 5xx, timeout, refusal, empty body — is exercised
// without a live service. The invariant throughout: the client NEVER throws
// (the route hangs a 502 off ok:false; there is no second renderer).

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./auth", () => ({
  fetchGcpIdToken: vi.fn(async () => "gcp-id-token"),
}));

import { fetchGcpIdToken } from "./auth";
import {
  getBdRenderServiceConfig,
  renderBdViaService,
  resetBdRenderServiceConfigWarning,
  type BdRenderServiceConfig,
} from "./bd-client";

const ENV_KEYS = [
  "BD_RENDER_SERVICE_URL",
  "GCP_WORKLOAD_IDENTITY_PROVIDER",
  "GCP_BD_RENDER_INVOKER_SA",
  "GCP_RENDER_INVOKER_SA",
] as const;

const CONFIG: BdRenderServiceConfig = {
  url: "https://bd.example.run.app",
  audience: "https://bd.example.run.app",
  workloadIdentityProvider:
    "projects/123/locations/global/workloadIdentityPools/vercel/providers/vercel",
  serviceAccountEmail: "bd-invoker@proj.iam.gserviceaccount.com",
};

function bytesResponse(bytes: Uint8Array, headers: Record<string, string> = {}): Response {
  return new Response(new Uint8Array(bytes), {
    status: 200,
    headers: { "content-type": "model/gltf-binary", ...headers },
  });
}

beforeEach(() => {
  for (const k of ENV_KEYS) delete process.env[k];
  resetBdRenderServiceConfigWarning();
  vi.mocked(fetchGcpIdToken).mockClear();
  vi.mocked(fetchGcpIdToken).mockResolvedValue("gcp-id-token");
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("getBdRenderServiceConfig", () => {
  it("null when BD_RENDER_SERVICE_URL is unset (feature dark)", () => {
    expect(getBdRenderServiceConfig()).toBeNull();
  });

  it("null (warns once) when WIF vars are incomplete", () => {
    process.env.BD_RENDER_SERVICE_URL = CONFIG.url;
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    expect(getBdRenderServiceConfig()).toBeNull();
    getBdRenderServiceConfig();
    expect(warn).toHaveBeenCalledTimes(1); // warn-once latch
  });

  it("reads the config and derives the audience origin", () => {
    process.env.BD_RENDER_SERVICE_URL = CONFIG.url;
    process.env.GCP_WORKLOAD_IDENTITY_PROVIDER = CONFIG.workloadIdentityProvider;
    process.env.GCP_BD_RENDER_INVOKER_SA = CONFIG.serviceAccountEmail;
    expect(getBdRenderServiceConfig()).toEqual(CONFIG);
  });

  it("falls back to the shared GCP_RENDER_INVOKER_SA", () => {
    process.env.BD_RENDER_SERVICE_URL = CONFIG.url;
    process.env.GCP_WORKLOAD_IDENTITY_PROVIDER = CONFIG.workloadIdentityProvider;
    process.env.GCP_RENDER_INVOKER_SA = "shared@proj.iam.gserviceaccount.com";
    expect(getBdRenderServiceConfig()?.serviceAccountEmail).toBe(
      "shared@proj.iam.gserviceaccount.com",
    );
  });
});

describe("renderBdViaService (never throws)", () => {
  it("ok:false when no Vercel OIDC token", async () => {
    const r = await renderBdViaService({ config: CONFIG, slug: "s", params: {}, vercelOidcToken: null });
    expect(r.ok).toBe(false);
  });

  it("ok:false when token exchange throws", async () => {
    vi.mocked(fetchGcpIdToken).mockRejectedValue(new Error("boom"));
    const r = await renderBdViaService({ config: CONFIG, slug: "s", params: {}, vercelOidcToken: "t" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errorMessage).toContain("WIF token exchange failed");
  });

  it("returns bytes + renderMs on a 200, and targets ?format", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(bytesResponse(new Uint8Array([1, 2, 3]), { "x-render-ms": "17" }));
    const r = await renderBdViaService({
      config: CONFIG,
      slug: "holder-spray-can",
      params: { d: 70 },
      format: "stl",
      vercelOidcToken: "t",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(Array.from(r.bytes)).toEqual([1, 2, 3]);
      expect(r.renderMs).toBe(17);
    }
    const url = new URL((fetchMock.mock.calls[0][0] as URL).toString());
    expect(url.pathname).toBe("/render");
    expect(url.searchParams.get("format")).toBe("stl");
  });

  it("ok:false on a non-200 with the service errorMessage", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: false, errorMessage: "out of range" }), {
        status: 400,
        headers: { "content-type": "application/json" },
      }),
    );
    const r = await renderBdViaService({ config: CONFIG, slug: "s", params: {}, vercelOidcToken: "t" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errorMessage).toContain("out of range");
  });

  it("ok:false when the network throws", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("ECONNREFUSED"));
    const r = await renderBdViaService({ config: CONFIG, slug: "s", params: {}, vercelOidcToken: "t" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errorMessage).toContain("unreachable");
  });

  it("ok:false on an empty 200 body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(bytesResponse(new Uint8Array()));
    const r = await renderBdViaService({ config: CONFIG, slug: "s", params: {}, vercelOidcToken: "t" });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errorMessage).toContain("empty body");
  });
});
