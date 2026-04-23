"use client";

// 3-column detail shell. Phase 1b composes three placeholder children
// so 1c can fill in the real chrome (stat strip, grid/axes overlay,
// grouped param rail with unit ornaments) without re-plumbing state.
//
// Columns: 240px quick-jump · flex viewer · 360px param rail.
// Collapses to a single column below the xl breakpoint (1200px).

import Link from "next/link";
import { useState } from "react";
import StlViewer from "./StlViewer";
import ParamForm from "./ParamForm";
import { useDetailState } from "@/hooks/useDetailState";
import { useRenderer, type RenderResult, type RenderState } from "@/hooks/useRenderer";
import type { Param, ParamValue } from "@/lib/scad-params/parse";

export interface DetailPageModel {
  title: string;
  modelPath: string;
  source: string;
  params: Param[];
  warnings: string[];
}

interface Props {
  model: DetailPageModel;
}

export default function DetailPage({ model }: Props) {
  const { state, setParam } = useDetailState(model.params);
  const render = useRenderer({
    modelPath: model.modelPath,
    source: model.source,
    params: model.params,
    values: state.params,
  });

  return (
    <div className="flex flex-col">
      <DetailHeader title={model.title} modelPath={model.modelPath} />
      <div className="grid grid-cols-1 xl:grid-cols-[240px_1fr_360px]">
        <DetailLeftRail
          modelPath={model.modelPath}
          history={render.history}
          state={render.state}
          warnings={model.warnings}
        />
        <ViewerChrome state={render.state} />
        <ParamRail
          params={model.params}
          values={state.params}
          onChange={setParam}
          modelPath={model.modelPath}
        />
      </div>
    </div>
  );
}

function DetailHeader({ title, modelPath }: { title: string; modelPath: string }) {
  return (
    <div className="flex items-baseline gap-12 border-b border-line bg-panel px-12 py-8">
      <Link
        href="/"
        className="text-11 text-text-dim no-underline hover:text-text"
      >
        ← all models
      </Link>
      <h1 className="m-0 text-14 font-semibold text-text">{title}</h1>
      <code className="font-mono text-10 text-text-mute">{modelPath}</code>
    </div>
  );
}

function DetailLeftRail({
  modelPath,
  history,
  state,
  warnings,
}: {
  modelPath: string;
  history: RenderResult[];
  state: RenderState;
  warnings: string[];
}) {
  // Reuses the show/hide toggle idiom from the old ModelStudio debug
  // panel — replaced by a proper source-browser in 1c, but useful now
  // as a quick-jump to the raw .scad path for debugging.
  const [showPath, setShowPath] = useState(false);
  const live = state.kind === "loading"
    ? { ms: state.kind === "loading" ? "…" : null, kb: null as string | null }
    : state.kind === "ready"
      ? { ms: formatMs(state.result.ms), kb: formatKb(state.result.stlBytes.byteLength) }
      : { ms: null, kb: null };

  return (
    <aside className="border-b border-line bg-panel p-10 xl:border-b-0 xl:border-r">
      <div className="text-10 uppercase tracking-wider text-text-mute">
        Source
      </div>
      <button
        type="button"
        onClick={() => setShowPath((s) => !s)}
        className="mt-4 rounded-3 border border-line bg-panel2 px-6 py-2 font-mono text-10 text-text-dim hover:border-accent-line"
      >
        {showPath ? "Hide path" : "Show path"}
      </button>
      {showPath && (
        <pre className="mt-6 overflow-auto rounded-3 border border-line bg-panel2 p-6 font-mono text-10 text-text-dim">
          {modelPath}
        </pre>
      )}

      <div className="mt-18 text-10 uppercase tracking-wider text-text-mute">
        Render log
      </div>
      <ul className="mt-4 flex flex-col gap-3 font-mono text-10">
        {state.kind === "loading" && (
          <li className="text-text-dim">rendering…</li>
        )}
        {state.kind === "error" && (
          <li className="text-red">{state.error.message}</li>
        )}
        {history.length === 0 && state.kind === "idle" && (
          <li className="text-text-mute">—</li>
        )}
        {history.map((h, i) => (
          <li
            key={i}
            className={i === 0 ? "text-text-dim" : "text-text-mute"}
          >
            {formatMs(h.ms)}ms · {formatKb(h.stlBytes.byteLength)}kb
          </li>
        ))}
        {live.ms != null && live.kb != null && history.length === 0 && (
          <li className="text-text-dim">{live.ms}ms · {live.kb}kb</li>
        )}
      </ul>

      {warnings.length > 0 && (
        <>
          <div className="mt-18 text-10 uppercase tracking-wider text-text-mute">
            Warnings
          </div>
          <ul className="mt-4 flex flex-col gap-3 font-mono text-10 text-warn">
            {warnings.map((w, i) => (
              <li key={i} className="text-warn opacity-70">{w}</li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}

function ViewerChrome({ state }: { state: RenderState }) {
  return (
    <section className="min-h-[480px] bg-panel2">
      {state.kind === "ready" && <StlViewer stl={state.result.stlBytes} />}
      {state.kind === "loading" && (
        <ViewerPlaceholder>rendering…</ViewerPlaceholder>
      )}
      {state.kind === "idle" && <ViewerPlaceholder>idle</ViewerPlaceholder>}
      {state.kind === "error" && (
        <ViewerPlaceholder className="text-red">
          <strong>render failed</strong>
          <pre className="mt-8 whitespace-pre-wrap text-11">{state.error.message}</pre>
        </ViewerPlaceholder>
      )}
    </section>
  );
}

function ViewerPlaceholder({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex h-[480px] items-center justify-center border border-line bg-panel2 text-text-dim ${className}`}
    >
      <div className="flex flex-col items-center">{children}</div>
    </div>
  );
}

function ParamRail({
  params,
  values,
  onChange,
  modelPath,
}: {
  params: Param[];
  values: Record<string, ParamValue>;
  onChange: (name: string, value: ParamValue) => void;
  modelPath: string;
}) {
  const [exportState, setExportState] = useState<ExportState>({ kind: "idle" });

  async function handleDownload() {
    setExportState({ kind: "exporting" });
    try {
      const res = await fetch("/api/export", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model: modelPath, params: values }),
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => "");
        let msg = `HTTP ${res.status}`;
        try { msg = JSON.parse(detail).error ?? msg; } catch { /* keep msg */ }
        setExportState({ kind: "error", message: msg });
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download =
        filenameFromContentDisposition(res.headers.get("content-disposition")) ??
        "model.stl";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportState({ kind: "idle" });
    } catch (e) {
      setExportState({
        kind: "error",
        message: e instanceof Error ? e.message : String(e),
      });
    }
  }

  return (
    <aside className="border-t border-line bg-panel p-12 xl:border-l xl:border-t-0">
      <ParamForm
        params={params}
        values={values}
        onChange={(next) => {
          // Diff-and-apply: ParamForm hands us the whole dict, but our
          // state hook prefers a per-key setter so we don't blow away
          // keys it didn't emit. All keys present → plain replace.
          for (const k of Object.keys(next)) {
            if (next[k] !== values[k]) onChange(k, next[k]);
          }
        }}
      />
      <button
        type="button"
        onClick={handleDownload}
        disabled={exportState.kind === "exporting"}
        className="mt-14 w-full rounded-4 border border-accent-line bg-accent px-8 py-6 text-12 font-semibold text-accent-ink disabled:cursor-wait disabled:opacity-60"
      >
        {exportState.kind === "exporting" ? "Exporting…" : "Download STL"}
      </button>
      {exportState.kind === "error" && (
        <p className="mt-6 text-11 text-red">
          export failed: {exportState.message}
        </p>
      )}
    </aside>
  );
}

type ExportState =
  | { kind: "idle" }
  | { kind: "exporting" }
  | { kind: "error"; message: string };

function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const m = header.match(/filename="([^"]+)"/);
  return m ? m[1] : null;
}

function formatMs(ms: number): string {
  return ms.toFixed(0);
}

function formatKb(bytes: number): string {
  return (bytes / 1024).toFixed(1);
}
