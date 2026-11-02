"use client";

import { useEffect, useId, useRef, useState } from "react";
import { fetchSpools, type BridgeSpool } from "@/lib/print-bridge/client";

type SpoolsState =
  | { kind: "loading" }
  | { kind: "ready"; spools: BridgeSpool[] }
  | { kind: "error"; message: string };

function spoolKey(spool: BridgeSpool | null): string {
  return spool ? `${spool.ams_id}:${spool.tray_id}` : "default";
}

function SpoolLabel({ spool }: { spool: BridgeSpool | null }) {
  if (!spool) return <>Recipe default</>;
  return <>
    {spool.colour && (
      <span
        role="img"
        aria-label={spool.colour}
        className="mr-4 inline-block h-[10px] w-[10px] rounded-2 border border-line"
        style={{ backgroundColor: spool.colour }}
      />
    )}
    {spool.material} {spool.name}
    {spool.remain_pct != null ? ` · ${spool.remain_pct}%` : ""}
    {spool.generic ? ` (generic ${spool.material} profile)` : ""}
    {!spool.resolved ? " (no slicer preset)" : ""}
  </>;
}

export default function SpoolPicker({ bridgeUrl, printerId, cache, value, onChange }: {
  bridgeUrl: string;
  printerId: number;
  cache: Map<number, Promise<BridgeSpool[]>>;
  value: BridgeSpool | null;
  onChange: (spool: BridgeSpool | null) => void;
}) {
  const [state, setState] = useState<SpoolsState>({ kind: "loading" });
  const [retry, setRetry] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLDivElement>(null);
  const id = useId();

  // Cache promises per printer for this dialog opening, including failures.
  // A late response for a previous printer/open must never update this picker.
  useEffect(() => {
    let live = true;
    setState({ kind: "loading" });
    let pending = cache.get(printerId);
    if (!pending) {
      pending = fetchSpools(bridgeUrl, printerId);
      cache.set(printerId, pending);
    }
    pending.then(
      (spools) => { if (live) setState({ kind: "ready", spools }); },
      (error: unknown) => {
        if (live) setState({ kind: "error", message: error instanceof Error ? error.message : "Could not load spools" });
      },
    );
    return () => { live = false; };
  }, [bridgeUrl, printerId, cache, retry]);

  useEffect(() => {
    if (expanded) list.current?.querySelector<HTMLButtonElement>('[aria-selected="true"]')?.focus();
  }, [expanded]);

  return (
    <div className="relative mt-8" onBlur={(event) => {
      if (!event.currentTarget.contains(event.relatedTarget)) setExpanded(false);
    }}>
      <span id={`${id}-label`} className="text-10 text-text-mute">Spool</span>
      {/* A listbox permits actual swatches; native option elements cannot reliably render them. */}
      <button
        ref={trigger}
        type="button"
        aria-labelledby={`${id}-label ${id}-value`}
        aria-haspopup="listbox"
        aria-expanded={expanded}
        aria-controls={expanded ? `${id}-list` : undefined}
        onClick={() => setExpanded((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setExpanded(true);
          }
        }}
        className="mt-2 block w-full rounded-3 border border-line bg-panel2 px-6 py-4 text-left"
      >
        <span id={`${id}-value`}><SpoolLabel spool={value} /></span> ▾
      </button>
      {expanded && (
        <div
          ref={list}
          id={`${id}-list`}
          role="listbox"
          aria-labelledby={`${id}-label`}
          className="absolute z-30 mt-2 max-h-[240px] w-full overflow-auto rounded-3 border border-line bg-panel shadow-modal"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              setExpanded(false);
              trigger.current?.focus();
            }
            const options = Array.from(list.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? []);
            const index = options.indexOf(document.activeElement as HTMLButtonElement);
            const next = event.key === "Home" ? 0 : event.key === "End" ? options.length - 1
              : event.key === "ArrowDown" ? (index + 1) % options.length
              : event.key === "ArrowUp" ? (index - 1 + options.length) % options.length : null;
            if (next !== null) {
              event.preventDefault();
              options[next]?.focus();
            }
          }}
        >
          {[null, ...(state.kind === "ready" ? state.spools : [])].map((spool) => (
            <button
              key={spoolKey(spool)}
              type="button"
              role="option"
              aria-selected={spoolKey(value) === spoolKey(spool)}
              disabled={spool !== null && !spool.resolved}
              tabIndex={-1}
              className="block w-full px-6 py-4 text-left hover:bg-panel-hi focus:bg-panel-hi disabled:opacity-60"
              onClick={() => {
                onChange(spool);
                setExpanded(false);
                trigger.current?.focus();
              }}
            >
              <SpoolLabel spool={spool} />
            </button>
          ))}
        </div>
      )}
      {state.kind === "loading" && <p className="mt-2 text-text-dim">Loading spools…</p>}
      {state.kind === "error" && (
        <div>
          <p role="status" className="mt-2 text-red">{state.message}</p>
          <button type="button" className="mt-4 rounded-3 border border-line bg-panel2 px-8 py-4 hover:bg-panel-hi" onClick={() => {
            cache.delete(printerId);
            onChange(null);
            setRetry((current) => current + 1);
          }}>Retry</button>
        </div>
      )}
    </div>
  );
}
