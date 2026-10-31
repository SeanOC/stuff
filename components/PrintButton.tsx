"use client";

// Print straight from a model page via the print bridge (pst-62i6h).
//
// Renders NOTHING unless NEXT_PUBLIC_PRINT_BRIDGE_URL is set AND a client-side
// GET {bridge}/health answers ok within 2 s — off-tailnet visitors (and every
// deploy without the env var) never see a button or an error. The request is
// the page's own Download target (see PrintTarget); the bridge picks STL vs
// 3MF from the printer model, so there is one Print button per page.

import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  fetchPrinters,
  fetchRun,
  getPrintBridgeUrl,
  probePrintBridge,
  startPrint,
  TERMINAL_RUN_STATES,
  type BridgePrinter,
  type PrintTarget,
  type RunStatus,
} from "@/lib/print-bridge/client";

export const POLL_INTERVAL_MS = 10_000;
/** The bridge passes Bambuddy's run status through un-normalised; an unknown
 *  status counts as non-terminal, so polling is capped instead of open-ended. */
export const POLL_CAP_MS = 20 * 60_000;

const COPIES = [1, 2, 3, 4, 5, 6, 7, 8, 9];

type PrintersState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; printers: BridgePrinter[] }
  | { kind: "error"; message: string };

type JobState =
  | { kind: "idle" }
  | { kind: "submitting" }
  | {
      kind: "queued";
      runId: number;
      printer: string;
      run: RunStatus | null;
      /** Polling ended at the cap without a known terminal status. */
      gaveUp: boolean;
    }
  | { kind: "conflict"; message: string; issues: string[] }
  | { kind: "error"; message: string };

function printerLabel(p: BridgePrinter): string {
  return p.name ?? `Printer ${p.id}`;
}

export default function PrintButton({
  target,
  variant,
  disabled = false,
}: {
  target: PrintTarget;
  /** "rail": full-width under the build123d Download; "strip": compact, in the
   *  SCAD viewer's bottom stat strip (popover opens upward). */
  variant: "rail" | "strip";
  disabled?: boolean;
}) {
  const bridgeUrl = getPrintBridgeUrl();
  const [available, setAvailable] = useState(false);
  const [open, setOpen] = useState(false);
  const [printers, setPrinters] = useState<PrintersState>({ kind: "idle" });
  const [printerId, setPrinterId] = useState<number | null>(null);
  const [copies, setCopies] = useState(1);
  const [job, setJob] = useState<JobState>({ kind: "idle" });

  useEffect(() => {
    if (!bridgeUrl) return;
    let live = true;
    probePrintBridge(bridgeUrl).then((ok) => {
      if (live) setAvailable(ok);
    });
    return () => {
      live = false;
    };
  }, [bridgeUrl]);

  // Load printers the first time the popover opens.
  useEffect(() => {
    if (!open || !bridgeUrl || printers.kind !== "idle") return;
    setPrinters({ kind: "loading" });
    fetchPrinters(bridgeUrl).then(
      (list) => {
        setPrinters({ kind: "ready", printers: list });
        setPrinterId((cur) => cur ?? list[0]?.id ?? null);
      },
      (e: unknown) =>
        setPrinters({
          kind: "error",
          message: e instanceof Error ? e.message : "could not load printers",
        }),
    );
  }, [open, bridgeUrl, printers.kind]);

  // Poll the queued run every 10 s until terminal (or the cap).
  const queuedRunId = job.kind === "queued" && !job.gaveUp ? job.runId : null;
  const terminal =
    job.kind === "queued" && job.run?.status != null && TERMINAL_RUN_STATES.has(job.run.status);
  const pollStart = useRef(0);
  useEffect(() => {
    if (queuedRunId === null || terminal || !bridgeUrl) return;
    if (pollStart.current === 0) pollStart.current = Date.now();
    const timer = setTimeout(async () => {
      let run: RunStatus | null = null;
      try {
        run = await fetchRun(bridgeUrl, queuedRunId);
      } catch {
        /* transient: keep the last-seen status and poll again */
      }
      const gaveUp = Date.now() - pollStart.current >= POLL_CAP_MS;
      setJob((cur) =>
        cur.kind === "queued" && cur.runId === queuedRunId
          ? { ...cur, run: run ?? cur.run, gaveUp }
          : cur,
      );
    }, POLL_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [queuedRunId, terminal, bridgeUrl, job]);

  const busy =
    job.kind === "submitting" || (job.kind === "queued" && !terminal && !job.gaveUp);

  const submit = useCallback(async () => {
    if (!bridgeUrl || printerId === null || busy) return;
    const printer =
      printers.kind === "ready" ? printers.printers.find((p) => p.id === printerId) : undefined;
    setJob({ kind: "submitting" });
    const result = await startPrint(bridgeUrl, target, printerId, copies);
    if (result.kind === "queued") {
      pollStart.current = 0;
      setJob({
        kind: "queued",
        runId: result.runId,
        printer: printer ? printerLabel(printer) : `printer ${printerId}`,
        run: null,
        gaveUp: false,
      });
    } else {
      setJob(result);
    }
  }, [bridgeUrl, printerId, busy, printers, target, copies]);

  if (!bridgeUrl || !available) return null;

  const selected =
    printers.kind === "ready" ? printers.printers.find((p) => p.id === printerId) : undefined;
  const strip = variant === "strip";

  return (
    <div className={clsx("relative", strip ? "font-sans text-12" : "mt-8")}>
      <button
        type="button"
        data-testid="print-button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
        className={clsx(
          "rounded-3 border border-line bg-panel2 font-semibold text-text",
          "hover:bg-panel-hi disabled:cursor-not-allowed disabled:opacity-60",
          strip ? "px-8 py-2" : "inline-flex w-full items-center justify-center px-8 py-6",
        )}
      >
        Print…
      </button>
      {open && (
        <div
          data-testid="print-popover"
          role="dialog"
          aria-label="Print"
          className={clsx(
            "z-20 rounded-3 border border-line bg-panel p-10 text-12 text-text",
            strip
              ? "absolute bottom-full right-0 mb-6 w-[280px] shadow-modal"
              : "mt-6 w-full",
          )}
        >
          {printers.kind === "loading" && <p className="text-text-dim">Loading printers…</p>}
          {printers.kind === "error" && (
            <p data-testid="print-printers-error" className="text-red">
              {printers.message}
            </p>
          )}
          {printers.kind === "ready" && printers.printers.length === 0 && (
            <p className="text-text-dim">The bridge lists no printers.</p>
          )}
          {printers.kind === "ready" && printers.printers.length > 0 && (
            <>
              <label className="block">
                <span className="text-10 text-text-mute">Printer</span>
                <select
                  data-testid="print-printer"
                  value={printerId ?? ""}
                  onChange={(e) => setPrinterId(Number(e.target.value))}
                  className="mt-2 block w-full rounded-3 border border-line bg-panel2 px-6 py-4"
                >
                  {printers.printers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {printerLabel(p)}
                      {p.model ? ` — ${p.model}` : ""}
                    </option>
                  ))}
                </select>
              </label>
              {selected?.plate_detection_calibrated === false && (
                <p data-testid="print-plate-hint" className="mt-4 text-10 text-text-mute">
                  Plate check not calibrated.
                </p>
              )}
              <div className="mt-8 flex items-end gap-8">
                <label className="block">
                  <span className="text-10 text-text-mute">Copies</span>
                  <select
                    data-testid="print-copies"
                    value={copies}
                    onChange={(e) => setCopies(Number(e.target.value))}
                    className="mt-2 block rounded-3 border border-line bg-panel2 px-6 py-4"
                  >
                    {COPIES.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  data-testid="print-submit"
                  onClick={submit}
                  disabled={busy || printerId === null}
                  className={clsx(
                    "flex-1 rounded-3 border border-accent-line bg-accent px-8 py-4",
                    "font-semibold text-accent-ink hover:opacity-90",
                    "disabled:cursor-wait disabled:opacity-60",
                  )}
                >
                  {job.kind === "submitting" ? "Sending…" : "Print"}
                </button>
              </div>
            </>
          )}
          <JobStatus job={job} terminal={terminal} />
        </div>
      )}
    </div>
  );
}

function JobStatus({ job, terminal }: { job: JobState; terminal: boolean }) {
  if (job.kind === "queued") {
    const run = job.run;
    return (
      <div data-testid="print-status" className="mt-8">
        <p>Queued on {job.printer}</p>
        {run && (
          <p data-testid="print-run" className="mt-2 font-mono text-10 text-text-dim">
            {run.status ?? "unknown"}
            {run.copies != null &&
              ` · ${run.copies_completed ?? 0}/${run.copies} done` +
                (run.copies_failed ? `, ${run.copies_failed} failed` : "")}
            {terminal && run.error_message ? ` · ${run.error_message}` : ""}
          </p>
        )}
        {job.gaveUp && !terminal && (
          <p data-testid="print-gave-up" className="mt-2 text-10 text-text-mute">
            Stopped checking after 20 min; last status shown.
          </p>
        )}
      </div>
    );
  }
  if (job.kind === "conflict") {
    return (
      <div data-testid="print-conflict" className="mt-8 text-red">
        <p>{job.message}</p>
        {job.issues.length > 0 && (
          <ul className="mt-2 list-disc pl-16 font-mono text-10">
            {job.issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  if (job.kind === "error") {
    return (
      <p data-testid="print-error" className="mt-8 text-red">
        {job.message}
      </p>
    );
  }
  return null;
}
