"use client";

// 3-column detail shell. 240px source quick-jump + render log ·
// flex viewer with grid overlay, axes, view tabs, and 36px stat strip ·
// 360px grouped param rail. Collapses to a single column below the xl
// breakpoint (1200px).

import Link from "next/link";
import { useState } from "react";
import clsx from "clsx";
import { ParamRail } from "./ParamRail";
import { ViewerChrome } from "./ViewerChrome";
import { useDetailState } from "@/hooks/useDetailState";
import {
  useRenderer,
  type RenderResult,
  type RenderState,
} from "@/hooks/useRenderer";
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
  const detail = useDetailState(model.params);
  const render = useRenderer({
    modelPath: model.modelPath,
    source: model.source,
    params: model.params,
    values: detail.state.params,
  });

  const downloadButton = (
    <DownloadButton
      modelPath={model.modelPath}
      values={detail.state.params}
      canDownload={render.state.kind === "ready"}
    />
  );

  // At ≥1200px, pin the layout to the viewport (minus the 38px sticky
  // top bar from AppShell) so the viewer never leaves the visible area.
  // The grid's three columns each get min-h-0 so they can shrink below
  // content size, and the two rails scroll internally while the viewer
  // stays fixed. Below 1200px we intentionally fall back to the natural
  // single-column scroll — phase 4 owns the mobile bottom-sheet design.
  // (st-fl4)
  return (
    <div
      data-testid="detail-root"
      className="flex flex-col min-[1200px]:h-[calc(100vh-38px)]"
    >
      <DetailHeader title={model.title} modelPath={model.modelPath} />
      <div className="grid flex-1 min-h-0 grid-cols-1 min-[1200px]:grid-cols-[240px_1fr_360px] min-[1200px]:grid-rows-[1fr]">
        <aside
          data-testid="detail-left-col"
          className="min-h-0 border-b border-line bg-panel min-[1200px]:overflow-y-auto min-[1200px]:border-b-0 min-[1200px]:border-r"
        >
          <DetailLeftRail
            modelPath={model.modelPath}
            history={render.history}
            state={render.state}
            warnings={model.warnings}
          />
        </aside>
        <div className="min-h-0 min-[1200px]:overflow-hidden">
          <ViewerChrome
            state={render.state}
            camera={detail.state.camera}
            showGrid={detail.state.showGrid}
            showDims={detail.state.showDims}
            setCamera={detail.setCamera}
            toggleGrid={detail.toggleGrid}
            toggleDims={detail.toggleDims}
            onRefresh={render.refresh}
            downloadSlot={downloadButton}
            history={render.history}
          />
        </div>
        <aside
          data-testid="param-rail-col"
          className="min-h-0 border-t border-line bg-panel min-[1200px]:overflow-y-auto min-[1200px]:border-l min-[1200px]:border-t-0"
        >
          <ParamRail
            params={model.params}
            values={detail.state.params}
            onChange={detail.setParam}
          />
        </aside>
      </div>
    </div>
  );
}

function DetailHeader({
  title,
  modelPath,
}: {
  title: string;
  modelPath: string;
}) {
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
  return (
    <div className="p-10">
      <div className="font-mono text-10 uppercase tracking-wide text-text-mute">
        Source
      </div>
      <div className="mt-4 block break-all font-mono text-10 text-text-dim">
        {modelPath}
      </div>

      <div className="mt-18 font-mono text-10 uppercase tracking-wide text-text-mute">
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
            {h.ms.toFixed(0)}ms · {(h.stlBytes.byteLength / 1024).toFixed(1)}kb
          </li>
        ))}
      </ul>

      {warnings.length > 0 && (
        <>
          <div className="mt-18 font-mono text-10 uppercase tracking-wide text-text-mute">
            Warnings
          </div>
          <ul className="mt-4 flex flex-col gap-3 font-mono text-10 text-warn">
            {warnings.map((w, i) => (
              <li key={i} className="text-warn opacity-70">
                {w}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function DownloadButton({
  modelPath,
  values,
  canDownload,
}: {
  modelPath: string;
  values: Record<string, ParamValue>;
  canDownload: boolean;
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
        try {
          msg = JSON.parse(detail).error ?? msg;
        } catch {
          /* keep msg */
        }
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
    <div className="flex items-center gap-8">
      {exportState.kind === "error" && (
        <span className="text-red">export failed: {exportState.message}</span>
      )}
      <button
        type="button"
        onClick={handleDownload}
        disabled={exportState.kind === "exporting" || !canDownload}
        className={clsx(
          "rounded-3 border border-accent-line bg-accent px-8 py-2",
          "font-semibold text-accent-ink",
          "disabled:cursor-not-allowed disabled:opacity-60",
          exportState.kind === "exporting" && "disabled:cursor-wait",
        )}
      >
        {exportState.kind === "exporting" ? "Exporting…" : "Download STL"}
      </button>
    </div>
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
