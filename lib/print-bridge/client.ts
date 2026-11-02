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
//   GET  /printers/{id}/spools → loaded spools with colour and preset resolution
//   POST /print      ← {source:"bd", slug, preset} | {source:"bd", slug, params}
//                      | {source:"scad", model, params}  + {printer_id, copies, spool?}
//                    → 202 {status_url, …} (spool prints have no run_id)
//                      409 {error, report?: {ok, issues[]}, run_id?,
//                           installed?: number[], pipeline?: number}  403/5xx {error}
//                      (installed + pipeline: error "nozzle mismatch", diameters in mm)
//   GET  status_url  → {status, copies, copies_completed, copies_failed, error_message, …}
//                      /runs/{id}, /queue/{id}, or /queue/batches/{id}

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

// Share in-flight probes and cache success for the page session. Failures are
// evicted so a later mount or visibility change can discover restored access.
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
    const pending = probe;
    void probe.then((ok) => {
      if (!ok && healthCache.get(bridgeUrl) === pending) healthCache.delete(bridgeUrl);
    });
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

export interface BridgeSpool {
  ams_id: number;
  tray_id: number;
  slot: number;
  material: string | null;
  name: string | null;
  colour: string | null;
  remain_pct: number | null;
  preset: string | null;
  generic: boolean;
  resolved: boolean;
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
  sliced_library_file_id?: number | null;
  jobs?: unknown[];
}

export const TERMINAL_RUN_STATES: ReadonlySet<string> = new Set([
  "completed",
  "failed",
  "partial_failure",
  "cancelled",
  "skipped",
]);

export type PrintResult =
  | { kind: "queued"; statusUrl: string }
  /** 409: the bridge's message plus each eligibility issue, verbatim. */
  | { kind: "conflict"; message: string; issues: string[] }
  | { kind: "error"; message: string };

export const READ_TIMEOUT_MS = 10_000;
export const PRINT_TIMEOUT_MS = 5 * 60_000;

/** One translation for transport failures and bridge HTTP errors. */
function errorMessage(body?: { error?: unknown } | null, status?: number): string {
  if (status === undefined) return "Print bridge unreachable. Are you on the tailnet?";
  if (typeof body?.error === "string") {
    if (status === 502 && body.error.startsWith("Bambuddy unreachable")) {
      return "Bambuddy is unreachable from the print bridge.";
    }
    return `${body.error} (HTTP ${status})`;
  }
  return `Print bridge error (HTTP ${status})`;
}

/** Keep the deadline active through body consumption, including error bodies. */
async function requestBridge(url: string, timeout: number, init?: RequestInit) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(url, { ...init, signal: ctrl.signal });
    const body = await res.json().catch((error: unknown) => {
      if (error instanceof SyntaxError) return null;
      throw error;
    });
    return { res, body };
  } catch {
    throw new Error(errorMessage());
  } finally {
    clearTimeout(timer);
  }
}

function issueText(issue: unknown): string {
  return typeof issue === "string" ? issue : JSON.stringify(issue);
}

export async function fetchPrinters(bridgeUrl: string): Promise<BridgePrinter[]> {
  const { res, body } = await requestBridge(`${bridgeUrl}/printers`, READ_TIMEOUT_MS);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  if (!Array.isArray(body)) throw new Error("Print bridge returned no printer list");
  return body as BridgePrinter[];
}

export async function fetchSpools(bridgeUrl: string, printerId: number): Promise<BridgeSpool[]> {
  const { res, body } = await requestBridge(`${bridgeUrl}/printers/${printerId}/spools`, READ_TIMEOUT_MS);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  if (!Array.isArray(body)) throw new Error("Print bridge returned no spool list");
  return body as BridgeSpool[];
}

/** One POST, never retried — a re-POST could start a second print. */
export async function startPrint(
  bridgeUrl: string,
  target: PrintTarget,
  printerId: number,
  copies: number,
  spool?: Pick<BridgeSpool, "ams_id" | "tray_id">,
): Promise<PrintResult> {
  try {
    const { res, body } = await requestBridge(`${bridgeUrl}/print`, PRINT_TIMEOUT_MS, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ ...target, printer_id: printerId, copies, ...(spool ? { spool } : {}) }),
    });
    if (res.status === 202) {
      if (typeof body?.status_url === "string" && body.status_url.startsWith("/")) {
        return { kind: "queued", statusUrl: body.status_url };
      }
      if (typeof body?.run_id === "number") return { kind: "queued", statusUrl: `/runs/${body.run_id}` };
      return { kind: "error", message: "Print bridge accepted the job but returned no status URL" };
    }
    if (res.status === 409) {
      const issues: unknown[] = Array.isArray(body?.report?.issues) ? body.report.issues : [];
      return {
        kind: "conflict",
        message: typeof body?.error === "string" ? body.error : "Printer is not eligible",
        issues: issues.map(issueText),
      };
    }
    return { kind: "error", message: errorMessage(body, res.status) };
  } catch {
    return { kind: "error", message: errorMessage() };
  }
}

export async function fetchRun(bridgeUrl: string, runId: number): Promise<RunStatus> {
  return fetchPrintStatus(bridgeUrl, `/runs/${runId}`);
}

export async function fetchPrintStatus(bridgeUrl: string, statusUrl: string): Promise<RunStatus> {
  const { res, body } = await requestBridge(`${bridgeUrl}${statusUrl}`, READ_TIMEOUT_MS);
  if (!res.ok) throw new Error(errorMessage(body, res.status));
  if (!body) throw new Error("Print bridge returned no run status");
  return body as RunStatus;
}
