// Client for the live build123d render service (services/bd-render/) —
// bead pst-6ugb (P2b of epic pst-7srz).
//
// The build123d analogue of client.ts (native OpenSCAD). /api/bd-render
// calls this on a cache MISS: build123d is Python/OCP and CANNOT run in a
// Vercel function or in the browser, so — unlike the SCAD path — there is
// NO WASM fallback. A service failure is a clean, structured error, not a
// silent degrade. The client still NEVER throws (returns { ok:false }); the
// route turns that into a 502, it doesn't fall back to a second renderer.
//
// The service's contract (services/bd-render/server.py):
//   POST /render?format=glb|stl   body { slug, params }
//   success: 200 + raw GLB bytes (model/gltf-binary) or STL (application/sla)
//   failure: 4xx/5xx + JSON { ok:false, errorMessage }
//
// Auth reuses lib/render-service/auth.ts fetchGcpIdToken() UNCHANGED: the
// same keyless Vercel-OIDC → WIF → invoker-SA impersonation the SCAD
// service uses, just pointed at the bd-render service's URL/audience/SA.

import { fetchGcpIdToken } from "./auth";
import type { ParamValue } from "@/lib/scad-params/parse";

export type BdRenderFormat = "glb" | "stl";

export interface BdRenderServiceConfig {
  /** Cloud Run service base URL (BD_RENDER_SERVICE_URL). */
  url: string;
  /** ID-token audience: the service URL's origin. */
  audience: string;
  /** WIF provider resource name (GCP_WORKLOAD_IDENTITY_PROVIDER, shared). */
  workloadIdentityProvider: string;
  /** bd-render invoker SA email (GCP_BD_RENDER_INVOKER_SA, or the shared SA). */
  serviceAccountEmail: string;
}

// A build123d render is sub-second warm locally; the service caps a
// pathological OCP hang at ~90s. 100s leaves room for a Cloud Run cold
// start on top of that while staying under the route's maxDuration.
const SERVICE_TIMEOUT_MS = 100_000;

let warnedIncompleteConfig = false;

/**
 * Read the bd-render config from env. Null means "bd live-render off":
 * either BD_RENDER_SERVICE_URL is unset (normal — feature dark) or the
 * WIF vars are missing (misconfig — warned once, then treated as off so
 * the route returns a clean 503 rather than crashing).
 *
 * Env:
 *   BD_RENDER_SERVICE_URL          — the Cloud Run service URL (gate)
 *   GCP_WORKLOAD_IDENTITY_PROVIDER — shared with the SCAD render service
 *   GCP_BD_RENDER_INVOKER_SA       — bd invoker SA; falls back to the
 *                                    shared GCP_RENDER_INVOKER_SA when the
 *                                    same SA is granted run.invoker on both.
 */
export function getBdRenderServiceConfig(): BdRenderServiceConfig | null {
  const url = process.env.BD_RENDER_SERVICE_URL;
  if (!url) return null;

  const workloadIdentityProvider = process.env.GCP_WORKLOAD_IDENTITY_PROVIDER;
  const serviceAccountEmail =
    process.env.GCP_BD_RENDER_INVOKER_SA ?? process.env.GCP_RENDER_INVOKER_SA;
  if (!workloadIdentityProvider || !serviceAccountEmail) {
    if (!warnedIncompleteConfig) {
      warnedIncompleteConfig = true;
      console.warn(
        "BD_RENDER_SERVICE_URL is set but GCP_WORKLOAD_IDENTITY_PROVIDER / " +
          "GCP_BD_RENDER_INVOKER_SA (or GCP_RENDER_INVOKER_SA) are not — " +
          "bd live-render disabled",
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
      console.warn(`BD_RENDER_SERVICE_URL is not a valid URL: ${url} — bd live-render disabled`);
    }
    return null;
  }

  return { url, audience, workloadIdentityProvider, serviceAccountEmail };
}

/** Test hook: reset the warn-once latch so each test observes the warn. */
export function resetBdRenderServiceConfigWarning(): void {
  warnedIncompleteConfig = false;
}

export type BdRenderResult =
  | { ok: true; bytes: Uint8Array; renderMs?: number }
  | { ok: false; errorMessage: string };

/**
 * Render (slug, params) via the bd-render service. NEVER throws: every
 * failure mode — missing OIDC token, token exchange, network, timeout,
 * non-200 — collapses to { ok:false, errorMessage }. There is no second
 * renderer to fall back to, so the caller surfaces this as a 502.
 */
export async function renderBdViaService(opts: {
  config: BdRenderServiceConfig;
  /** Manifest slug (service re-validates against its registry). */
  slug: string;
  /** Fully-resolved param values (defaults filled — matches the cache key). */
  params: Record<string, ParamValue>;
  /** glb for the in-page viewer, stl for download. Defaults to glb. */
  format?: BdRenderFormat;
  /** This request's Vercel OIDC token, if present. */
  vercelOidcToken: string | null;
  timeoutMs?: number;
}): Promise<BdRenderResult> {
  const { config } = opts;
  const format = opts.format ?? "glb";
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
    const target = new URL("/render", config.url);
    target.searchParams.set("format", format);
    res = await fetch(target, {
      method: "POST",
      headers: {
        authorization: `Bearer ${idToken}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({ slug: opts.slug, params: opts.params }),
      signal: AbortSignal.timeout(opts.timeoutMs ?? SERVICE_TIMEOUT_MS),
    });
  } catch (e) {
    return {
      ok: false,
      errorMessage: `bd-render service unreachable: ${e instanceof Error ? e.message : String(e)}`,
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
    return { ok: false, errorMessage: `bd-render service HTTP ${res.status}${detail}` };
  }

  let bytes: Uint8Array;
  try {
    bytes = new Uint8Array(await res.arrayBuffer());
  } catch (e) {
    return {
      ok: false,
      errorMessage: `bd-render service body read failed: ${e instanceof Error ? e.message : String(e)}`,
    };
  }
  if (bytes.byteLength === 0) {
    // Mirrors the service's own empty-mesh guard; belt and braces so an
    // empty body can never be cached or served as a model.
    return { ok: false, errorMessage: "bd-render service returned an empty body" };
  }

  const renderMsHeader = res.headers.get("x-render-ms");
  const renderMs = renderMsHeader === null ? undefined : Number(renderMsHeader);
  return {
    ok: true,
    bytes,
    renderMs: Number.isFinite(renderMs) ? renderMs : undefined,
  };
}
