// Client for the native render service (services/render/) — st-d32.
//
// /api/export calls this on a cache MISS when RENDER_SERVICE_URL is set:
// native OpenSCAD renders in low seconds vs ~22s for openscad-wasm. The
// whole path is flag-gated and non-throwing by design:
//
//   - RENDER_SERVICE_URL unset            -> getRenderServiceConfig() is
//     null and the route behaves exactly as before (WASM-only). Ships dark.
//   - URL set but WIF env incomplete      -> warn once per process, treat
//     as disabled (null) rather than erroring every export.
//   - auth/network/timeout/5xx at runtime -> renderViaService returns
//     { ok:false, ... } (never throws), and the route falls back to WASM.
//
// The service's POST /render contract (services/render/server.ts): 200 +
// application/sla + raw STL bytes on success (x-render-ms header), JSON
// { ok:false, errorMessage } on failure.

import type { ParamValue } from "@/lib/scad-params/parse";
import { fetchGcpIdToken } from "./auth";

export interface RenderServiceConfig {
  /** Cloud Run service base URL (RENDER_SERVICE_URL). */
  url: string;
  /** ID-token audience: the service URL's origin. */
  audience: string;
  /** WIF provider resource name (GCP_WORKLOAD_IDENTITY_PROVIDER). */
  workloadIdentityProvider: string;
  /** render-invoker SA email (GCP_RENDER_INVOKER_SA). */
  serviceAccountEmail: string;
}

// The service render is ~6.5s warm on the heaviest model; 45s leaves room
// for a Cloud Run cold start while still fitting a WASM fallback render
// (~22s) inside the route's maxDuration=120.
const SERVICE_TIMEOUT_MS = 45_000;

let warnedIncompleteConfig = false;

/**
 * Read the native-render config from env. Null means "native path off":
 * either the flag is unset (normal) or the WIF vars are missing (misconfig
 * — warned, then treated as off so exports keep working via WASM).
 */
export function getRenderServiceConfig(): RenderServiceConfig | null {
  const url = process.env.RENDER_SERVICE_URL;
  if (!url) return null;

  const workloadIdentityProvider = process.env.GCP_WORKLOAD_IDENTITY_PROVIDER;
  const serviceAccountEmail = process.env.GCP_RENDER_INVOKER_SA;
  if (!workloadIdentityProvider || !serviceAccountEmail) {
    if (!warnedIncompleteConfig) {
      warnedIncompleteConfig = true;
      console.warn(
        "RENDER_SERVICE_URL is set but GCP_WORKLOAD_IDENTITY_PROVIDER / " +
          "GCP_RENDER_INVOKER_SA are not — native render disabled, using WASM",
      );
    }
    return null;
  }

  let audience: string;
  try {
    audience = new URL(url).origin;
  } catch {
    if (!warnedIncompleteConfig) {
      warnedIncompleteConfig = true;
      console.warn(`RENDER_SERVICE_URL is not a valid URL: ${url} — native render disabled`);
    }
    return null;
  }

  return { url, audience, workloadIdentityProvider, serviceAccountEmail };
}

/** Test hook: reset the warn-once latch so each test observes the warn. */
export function resetRenderServiceConfigWarning(): void {
  warnedIncompleteConfig = false;
}

export interface ServiceRenderResult {
  ok: boolean;
  /** Raw STL bytes; present only when ok. */
  stl?: Uint8Array;
  /** Service-side render wall time (x-render-ms), when reported. */
  renderMs?: number;
  /** Why the call failed; present only when !ok. */
  errorMessage?: string;
}

/**
 * Render (model, params) via the native service. NEVER throws: every
 * failure mode — missing OIDC token, token exchange, network, timeout,
 * non-200 — collapses to { ok:false, errorMessage } so the caller's
 * fallback is a plain `if`.
 */
export async function renderViaService(opts: {
  config: RenderServiceConfig;
  /** Validated model path, e.g. "models/foo.scad" (service re-validates). */
  model: string;
  /** Fully-resolved param values (defaults filled in). */
  params: Record<string, ParamValue>;
  /** This request's Vercel OIDC token, if present. */
  vercelOidcToken: string | null;
  timeoutMs?: number;
}): Promise<ServiceRenderResult> {
  const { config } = opts;
  if (!opts.vercelOidcToken) {
    return { ok: false, errorMessage: "no Vercel OIDC token on this request" };
  }

  let idToken: string;
  try {
    idToken = await fetchGcpIdToken({
      vercelOidcToken: opts.vercelOidcToken,
      workloadIdentityProvider: config.workloadIdentityProvider,
      serviceAccountEmail: config.serviceAccountEmail,
      audience: config.audience,
    });
  } catch (e) {
    return {
      ok: false,
      errorMessage: `WIF token exchange failed: ${e instanceof Error ? e.message : String(e)}`,
    };
  }

  let res: Response;
  try {
    res = await fetch(new URL("/render", config.url), {
      method: "POST",
      headers: {
        authorization: `Bearer ${idToken}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ model: opts.model, params: opts.params }),
      signal: AbortSignal.timeout(opts.timeoutMs ?? SERVICE_TIMEOUT_MS),
    });
  } catch (e) {
    return {
      ok: false,
      errorMessage: `render service unreachable: ${e instanceof Error ? e.message : String(e)}`,
    };
  }

  if (!res.ok) {
    // Failure body is JSON { ok:false, errorMessage } per the service
    // contract, but never trust that shape from a 5xx.
    let detail = "";
    try {
      const body = (await res.json()) as { errorMessage?: string };
      if (typeof body?.errorMessage === "string") detail = `: ${body.errorMessage}`;
    } catch {
      // non-JSON error body — status alone is the diagnostic
    }
    return { ok: false, errorMessage: `render service HTTP ${res.status}${detail}` };
  }

  let stl: Uint8Array;
  try {
    stl = new Uint8Array(await res.arrayBuffer());
  } catch (e) {
    return {
      ok: false,
      errorMessage: `render service body read failed: ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  if (stl.byteLength === 0) {
    // Mirrors the service's own empty-STL guard; belt and braces so an
    // empty body can never be cached or served as a model.
    return { ok: false, errorMessage: "render service returned an empty body" };
  }

  const renderMsHeader = res.headers.get("x-render-ms");
  const renderMs = renderMsHeader === null ? undefined : Number(renderMsHeader);
  return {
    ok: true,
    stl,
    renderMs: Number.isFinite(renderMs) ? renderMs : undefined,
  };
}
