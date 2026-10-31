// Browser client for the print bridge (bridge/, bead pst-8amdt) — pst-62i6h.
//
// The bridge runs on cubert, reachable only on the tailnet (fronted by
// `tailscale serve --https`). The browser talks to it DIRECTLY: there is no
// stuff API route and no server code on this side, and no credential either —
// the bridge authorises POST /print from the Tailscale-User-Login header that
// `tailscale serve` injects. CORS is the bridge's job (ALLOWED_ORIGIN).
//
// Contract (bridge/README.md):
//   GET  /health     → {ok, bambuddy_reachable}
//   GET  /printers   → [{id, name, model, state, plate_detection_calibrated, pipeline,
//                        nozzle_mm}]
//   POST /print      ← {source:"bd", slug, preset} | {source:"bd", slug, params}
//                      | {source:"scad", model, params}  + {printer_id, copies}
//                    → 202 {library_file_id, run_id, status_url}
//                      409 {error, report?: {ok, issues[]}, run_id?,
//                           installed?: number[], pipeline?: number}  403/5xx {error}
//                      (installed + pipeline: error "nozzle mismatch", diameters in mm)
//   GET  /runs/{id}  → {status, copies, copies_completed, copies_failed, error_message, …}

import type { ParamValue } from "@/lib/scad-params/parse";

/**
 * The bridge base URL, or null when the feature is off. NEXT_PUBLIC_ vars are
 * inlined at BUILD time, and only for a literal `process.env.NAME` read —
 * enabling the button means setting the var in the Vercel env and rebuilding.
 */
export function getPrintBridgeUrl(): string | null {
  const url = process.env.NEXT_PUBLIC_PRINT_BRIDGE_URL;
  if (!url) return null;
  return url.replace(/\/+$/, "");
}

export const HEALTH_TIMEOUT_MS = 2_000;

// One probe per bridge URL per page session; the negative result is cached
// the same way as the positive one (an off-tailnet visitor probes once).
const healthCache = new Map<string, Promise<boolean>>();

/** Test hook: forget cached health probes. */
export function resetPrintBridgeHealthCache(): void {
  healthCache.clear();
}

/**
 * True only when the bridge answers GET /health within 2 s with
 * `{ok: true, bambuddy_reachable: true}` — a bridge whose Bambuddy is down
 * would 502 the first Print click, so it counts as unavailable. Never throws.
 */
export function probePrintBridge(bridgeUrl: string): Promise<boolean> {
  let probe = healthCache.get(bridgeUrl);
  if (!probe) {
    probe = (async () => {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), HEALTH_TIMEOUT_MS);
      try {
        const res = await fetch(`${bridgeUrl}/health`, { signal: ctrl.signal });
        if (!res.ok) return false;
        const body = await res.json();
        return body?.ok === true && body?.bambuddy_reachable === true;
      } catch {
        return false;
      } finally {
        clearTimeout(timer);
      }
    })();
    healthCache.set(bridgeUrl, probe);
  }
  return probe;
}

export interface BridgePrinter {
  id: number;
  name: string | null;
  model: string | null;
  state: string | null;
  plate_detection_calibrated: boolean | null;
  pipeline: string | null;
  /** Installed nozzle diameters in mm; [] when unknown. Absent from bridges before pst-0y0w4. */
  nozzle_mm?: number[];
}

/** What to print — mirrors exactly what the page's Download button fetches. */
export type PrintTarget =
  | { source: "bd"; slug: string; preset: string }
  | { source: "bd"; slug: string; params: Record<string, ParamValue> }
  | { source: "scad"; model: string; params: Record<string, ParamValue> };

/**
 * build123d target: the baked manifest preset while the controls equal it
 * (`bakedPresetId`, computed by BdDetailPage for its Download button), else
 * the live params.
 */
export function bdPrintTarget(
  slug: string,
  bakedPresetId: string | null,
  values: Record<string, ParamValue>,
): PrintTarget {
  return bakedPresetId
    ? { source: "bd", slug, preset: bakedPresetId }
    : { source: "bd", slug, params: values };
}

export interface RunStatus {
  status: string | null;
  copies: number | null;
  copies_completed: number | null;
  copies_failed: number | null;
  error_message: string | null;
}

export const TERMINAL_RUN_STATES: ReadonlySet<string> = new Set([
  "completed",
  "failed",
  "partial_failure",
  "cancelled",
]);

export type PrintResult =
  | { kind: "queued"; runId: number }
  /** 409: the bridge's message plus each eligibility issue, verbatim. */
  | { kind: "conflict"; message: string; issues: string[] }
  | { kind: "error"; message: string };

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.error === "string") return `${body.error} (HTTP ${res.status})`;
  } catch {
    /* fall through */
  }
  return `Print bridge error (HTTP ${res.status})`;
}

function issueText(issue: unknown): string {
  return typeof issue === "string" ? issue : JSON.stringify(issue);
}

export async function fetchPrinters(bridgeUrl: string): Promise<BridgePrinter[]> {
  const res = await fetch(`${bridgeUrl}/printers`);
  if (!res.ok) throw new Error(await errorMessage(res));
  const body = await res.json();
  if (!Array.isArray(body)) throw new Error("Print bridge returned no printer list");
  return body as BridgePrinter[];
}

/** One POST, never retried — a re-POST could start a second print. */
export async function startPrint(
  bridgeUrl: string,
  target: PrintTarget,
  printerId: number,
  copies: number,
): Promise<PrintResult> {
  let res: Response;
  try {
    res = await fetch(`${bridgeUrl}/print`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...target, printer_id: printerId, copies }),
    });
  } catch (e) {
    return { kind: "error", message: e instanceof Error ? e.message : "network error" };
  }
  if (res.status === 202) {
    const body = await res.json().catch(() => null);
    if (typeof body?.run_id === "number") return { kind: "queued", runId: body.run_id };
    return { kind: "error", message: "Print bridge accepted the job but returned no run id" };
  }
  if (res.status === 409) {
    const body = await res.json().catch(() => null);
    const issues: unknown[] = Array.isArray(body?.report?.issues) ? body.report.issues : [];
    return {
      kind: "conflict",
      message: typeof body?.error === "string" ? body.error : "Printer is not eligible",
      issues: issues.map(issueText),
    };
  }
  return { kind: "error", message: await errorMessage(res) };
}

export async function fetchRun(bridgeUrl: string, runId: number): Promise<RunStatus> {
  const res = await fetch(`${bridgeUrl}/runs/${runId}`);
  if (!res.ok) throw new Error(await errorMessage(res));
  return (await res.json()) as RunStatus;
}
