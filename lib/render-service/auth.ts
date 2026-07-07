// Keyless Vercel-OIDC -> Google Cloud auth for the native render service
// (st-d32, Phase 2 of st-rtb).
//
// The operator locked KEYLESS auth: no service-account JSON key is ever
// stored. Instead, each cache-miss request exchanges the per-invocation
// Vercel OIDC token for a Google ID token via Workload Identity
// Federation:
//
//   Vercel OIDC token (x-vercel-oidc-token header / VERCEL_OIDC_TOKEN env)
//     -> STS token exchange against the Workload Identity Pool provider
//        (google-auth-library ExternalAccountClient, the supported path)
//     -> impersonate the render-invoker service account
//        (Impersonated.fetchIdToken -> iamcredentials generateIdToken)
//     -> Google-signed ID token with audience = the Cloud Run service URL.
//
// Cloud Run (deployed auth-required, NO --allow-unauthenticated) verifies
// that ID token and the invoker SA's roles/run.invoker grant. The Vercel
// principalSet needs roles/iam.workloadIdentityUser on the SA — that role
// carries the getOpenIdToken permission the impersonation step uses.
//
// Clients are built per call, not cached: the Vercel OIDC token rotates
// per invocation, and this path only runs on a cache MISS where the
// render itself costs seconds — two extra token round-trips are noise.

import { ExternalAccountClient, Impersonated } from "google-auth-library";

export interface WifIdTokenOptions {
  /** The current request's Vercel OIDC token (rotates per invocation). */
  vercelOidcToken: string;
  /**
   * WIF provider resource name:
   * projects/<num>/locations/global/workloadIdentityPools/<pool>/providers/<provider>
   * (a leading //iam.googleapis.com/ prefix is accepted and stripped).
   */
  workloadIdentityProvider: string;
  /** Email of the render-invoker SA (has roles/run.invoker on the service). */
  serviceAccountEmail: string;
  /** ID-token audience — the Cloud Run service's root URL. */
  audience: string;
}

/**
 * Exchange a Vercel OIDC token for a Google-signed ID token that Cloud Run
 * will accept. Throws on any exchange/impersonation failure — the caller
 * (renderViaService) converts that into a non-throwing ok:false so the
 * export route can fall back to WASM.
 */
export async function fetchGcpIdToken(opts: WifIdTokenOptions): Promise<string> {
  const provider = opts.workloadIdentityProvider.replace(
    /^\/\/iam\.googleapis\.com\//,
    "",
  );

  // Federate: Vercel OIDC -> STS access token for the pool identity. The
  // supplier hands STS the raw Vercel token; google-auth-library owns the
  // exchange protocol. No impersonation URL here — the ID-token mint below
  // is a separate, explicit step so the flow stays one-impersonation-deep.
  const sourceClient = ExternalAccountClient.fromJSON({
    type: "external_account",
    audience: `//iam.googleapis.com/${provider}`,
    subject_token_type: "urn:ietf:params:oauth:token-type:jwt",
    token_url: "https://sts.googleapis.com/v1/token",
    subject_token_supplier: {
      getSubjectToken: async () => opts.vercelOidcToken,
    },
  });
  if (!sourceClient) {
    throw new Error("failed to construct WIF external-account client");
  }
  sourceClient.scopes = ["https://www.googleapis.com/auth/cloud-platform"];

  // Impersonate the invoker SA and mint an ID token for the Cloud Run
  // audience. includeEmail so Cloud Run's IAM check sees the SA identity.
  const impersonated = new Impersonated({
    sourceClient,
    targetPrincipal: opts.serviceAccountEmail,
    targetScopes: ["https://www.googleapis.com/auth/cloud-platform"],
  });
  return impersonated.fetchIdToken(opts.audience, { includeEmail: true });
}
