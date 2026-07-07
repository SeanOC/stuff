// Wiring tests for the Vercel-OIDC -> WIF -> ID-token exchange (st-d32).
// google-auth-library is mocked: these assert we construct the external-
// account client and the impersonation hop with exactly the shape GCP's
// STS + iamcredentials expect — the parts a typo would silently break and
// only a live 403 would otherwise reveal.

import { beforeEach, describe, expect, it, vi } from "vitest";

const { fromJSONMock, impersonatedCtor, fetchIdTokenMock } = vi.hoisted(() => {
  const fetchIdTokenMock = vi.fn(async () => "signed-id-token");
  return {
    fetchIdTokenMock,
    fromJSONMock: vi.fn((_cfg: Record<string, unknown>) => ({
      scopes: undefined as unknown,
    })),
    impersonatedCtor: vi.fn(function (
      this: { fetchIdToken: typeof fetchIdTokenMock },
      _opts: Record<string, unknown>,
    ) {
      this.fetchIdToken = fetchIdTokenMock;
    }),
  };
});

vi.mock("google-auth-library", () => ({
  ExternalAccountClient: { fromJSON: fromJSONMock },
  Impersonated: impersonatedCtor,
}));

import { fetchGcpIdToken } from "./auth";

const OPTS = {
  vercelOidcToken: "vercel-oidc-jwt",
  workloadIdentityProvider:
    "projects/123/locations/global/workloadIdentityPools/vercel/providers/vercel",
  serviceAccountEmail: "render-invoker@proj.iam.gserviceaccount.com",
  audience: "https://render.example.run.app",
};

beforeEach(() => {
  fromJSONMock.mockClear();
  impersonatedCtor.mockClear();
  fetchIdTokenMock.mockClear();
});

describe("fetchGcpIdToken", () => {
  it("exchanges via STS then impersonates the invoker SA for an ID token", async () => {
    const token = await fetchGcpIdToken(OPTS);
    expect(token).toBe("signed-id-token");

    // External-account (STS) config: pool-provider audience, JWT subject
    // type, and a supplier that yields the raw Vercel token.
    expect(fromJSONMock).toHaveBeenCalledOnce();
    const cfg = fromJSONMock.mock.calls[0][0];
    expect(cfg.type).toBe("external_account");
    expect(cfg.audience).toBe(
      `//iam.googleapis.com/${OPTS.workloadIdentityProvider}`,
    );
    expect(cfg.subject_token_type).toBe("urn:ietf:params:oauth:token-type:jwt");
    expect(cfg.token_url).toBe("https://sts.googleapis.com/v1/token");
    const supplier = cfg.subject_token_supplier as {
      getSubjectToken: () => Promise<string>;
    };
    await expect(supplier.getSubjectToken()).resolves.toBe("vercel-oidc-jwt");

    // Impersonation hop: the invoker SA, ID token minted for the Cloud Run
    // audience with the SA email embedded (Cloud Run's IAM check needs it).
    expect(impersonatedCtor).toHaveBeenCalledOnce();
    const impArgs = impersonatedCtor.mock.calls[0][0];
    expect(impArgs.targetPrincipal).toBe(OPTS.serviceAccountEmail);
    expect(impArgs.sourceClient).toBe(fromJSONMock.mock.results[0].value);
    expect(fetchIdTokenMock).toHaveBeenCalledWith(OPTS.audience, {
      includeEmail: true,
    });
  });

  it("strips a //iam.googleapis.com/ prefix rather than doubling it", async () => {
    await fetchGcpIdToken({
      ...OPTS,
      workloadIdentityProvider: `//iam.googleapis.com/${OPTS.workloadIdentityProvider}`,
    });
    const cfg = fromJSONMock.mock.calls[0][0];
    expect(cfg.audience).toBe(
      `//iam.googleapis.com/${OPTS.workloadIdentityProvider}`,
    );
  });

  it("throws when the client factory returns null (caller converts to fallback)", async () => {
    fromJSONMock.mockReturnValueOnce(null as never);
    await expect(fetchGcpIdToken(OPTS)).rejects.toThrow(/external-account client/);
  });

  it("propagates impersonation failures", async () => {
    fetchIdTokenMock.mockRejectedValueOnce(new Error("permission denied"));
    await expect(fetchGcpIdToken(OPTS)).rejects.toThrow("permission denied");
  });
});
