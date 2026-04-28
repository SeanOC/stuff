"use client";

// 3-column detail shell. 240px source quick-jump + preset list + render log ·
// flex viewer with grid overlay, axes, view tabs, and 36px stat strip ·
// 360px grouped param rail. Collapses to a single column below the xl
// breakpoint (1200px).

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import {
  AccessoriesSection,
  type DetailPageAccessory,
} from "./AccessoriesSection";
import { ParamRail } from "./ParamRail";
import { ViewerChrome } from "./ViewerChrome";
import { useDetailState } from "@/hooks/useDetailState";
import {
  useRenderer,
  type RenderState,
} from "@/hooks/useRenderer";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { useShortcut } from "@/hooks/useShortcut";
import { useUI } from "@/contexts/UIContext";
import type { Param, ParamValue, Preset } from "@/lib/scad-params/parse";
import type { RenderResult } from "@/hooks/useRenderer";

export interface DetailPageModel {
  title: string;
  slug: string;
  modelPath: string;
  source: string;
  params: Param[];
  presets: Preset[];
  warnings: string[];
}

// `DetailPageAccessory` lives in components/AccessoriesSection so the
// client bundle never imports lib/accessories/discover (which pulls
// node:fs/promises). Re-exported here for callers that import from
// DetailPage.
export type { DetailPageAccessory } from "./AccessoriesSection";

interface Props {
  model: DetailPageModel;
  /** M:N accessories compatible with this model. Empty list = no UI. */
  accessories?: DetailPageAccessory[];
}

export default function DetailPage({ model, accessories = [] }: Props) {
  const detail = useDetailState({
    params: model.params,
    stockPresets: model.presets,
    slug: model.slug,
  });
  const render = useRenderer({
    modelPath: model.modelPath,
    source: model.source,
    params: model.params,
    values: detail.state.params,
  });
  const { modal, setDetail } = useUI();

  const downloadRef = useRef<() => void>(() => {});
  const [saveRowOpen, setSaveRowOpen] = useState(false);
  // Left-rail collapsed state at ≥1200px (st-j98). At smaller widths
  // the layout stacks and this flag is unused.
  const [leftRailCollapsed, setLeftRailCollapsed] =
    useLocalStorage<boolean>("stuff.v1.detail.leftRailCollapsed", true);
  // Mobile/tablet (<1200px) disclosure state for the metadata pane
  // (st-yxj). Default closed so visitors land on the viewer + params
  // rather than a wall of metadata. Persisted under the same prefix
  // pattern as the desktop collapse flag.
  const [mobileMetadataOpen, setMobileMetadataOpen] =
    useLocalStorage<boolean>("stuff.v1.detail.mobileMetadataOpen", false);

  // Auto-fire the first render on mount (st-2y4). Phase 2b shipped a
  // deliberate idle-until-Enter gate per Caliper spec §Loading/Empty
  // (docs/design/caliper/README.md:58), reasoning that WASM compile +
  // three.js init is pricey if the visitor just leaves the tab. For
  // this project (≤5 models, personal tool) that trade-off doesn't
  // pencil out — every visit wants the preview. The idle UI + press-⏎
  // hint + disabled Download STL all stay in the tree as the error-
  // recovery path: a render failure drops back to idle and the user
  // presses Enter to retry. refresh() is idempotent when the render
  // is already live, so double-firing is harmless.
  useEffect(() => {
    if (render.state.kind === "idle") render.refresh();
    // Mount-only on purpose. `render.refresh` is stable but listing it
    // here risks retriggering on re-renders that happen to clear the
    // idle state momentarily — we want one fire, ever.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Publish a bridge to the command palette so the Actions / Presets
  // groups can dispatch download/save/load against this page (st-3lc).
  // Cleared on unmount + whenever the bridge's shape changes so the
  // palette never fires stale handles after a route change.
  useEffect(() => {
    const canDownload = render.state.kind === "ready";
    setDetail({
      slug: model.slug,
      title: model.title,
      presets: detail.allPresets,
      canDownload,
      downloadStl: () => downloadRef.current(),
      loadPreset: (id: string) => detail.loadPreset(id),
      openSaveRow: () => setSaveRowOpen(true),
    });
    return () => setDetail(null);
  }, [
    model.slug,
    model.title,
    detail.allPresets,
    detail.loadPreset,
    render.state.kind,
    setDetail,
  ]);

  // Recent-models LRU — last 5 distinct slugs, most-recent first. Read
  // by CommandPalette's Recent group (st-3lc).
  useEffect(() => {
    const key = "stuff.v1.recent.models";
    try {
      const raw = localStorage.getItem(key);
      const prev: unknown = raw ? JSON.parse(raw) : [];
      const prevSlugs = Array.isArray(prev)
        ? prev.filter((s): s is string => typeof s === "string")
        : [];
      const next = [model.slug, ...prevSlugs.filter((s) => s !== model.slug)].slice(0, 5);
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      // localStorage unavailable (SSR never reaches this effect; test
      // env may quota-exceed) — silently skip the LRU this visit.
    }
  }, [model.slug]);

  // ⌘E downloads the STL from anywhere on the detail page. Gates on
  // render.state === "ready" so we don't POST an empty body before
  // the first render completes.
  useShortcut(
    "$mod+e",
    () => {
      if (render.state.kind === "ready") downloadRef.current();
    },
    { enabled: modal.kind === "none" },
  );

  // ⌘1–⌘9 pick a preset by flat-list index (stock first, then user).
  useShortcut("$mod+1", () => detail.loadPresetByIndex(1), { enabled: modal.kind === "none" });
  useShortcut("$mod+2", () => detail.loadPresetByIndex(2), { enabled: modal.kind === "none" });
  useShortcut("$mod+3", () => detail.loadPresetByIndex(3), { enabled: modal.kind === "none" });
  useShortcut("$mod+4", () => detail.loadPresetByIndex(4), { enabled: modal.kind === "none" });
  useShortcut("$mod+5", () => detail.loadPresetByIndex(5), { enabled: modal.kind === "none" });
  useShortcut("$mod+6", () => detail.loadPresetByIndex(6), { enabled: modal.kind === "none" });
  useShortcut("$mod+7", () => detail.loadPresetByIndex(7), { enabled: modal.kind === "none" });
  useShortcut("$mod+8", () => detail.loadPresetByIndex(8), { enabled: modal.kind === "none" });
  useShortcut("$mod+9", () => detail.loadPresetByIndex(9), { enabled: modal.kind === "none" });

  // ⌘S opens the inline save-preset row in the left rail. No modal.
  useShortcut(
    "$mod+s",
    () => setSaveRowOpen(true),
    { enabled: modal.kind === "none" },
  );

  const downloadButton = (
    <DownloadButton
      modelPath={model.modelPath}
      values={detail.state.params}
      canDownload={render.state.kind === "ready"}
      registerHandler={(fn) => {
        downloadRef.current = fn;
      }}
    />
  );

  // At ≥1200px, pin the layout to the viewport (minus the 38px sticky
  // top bar from AppShell) so the viewer never leaves the visible area.
  // The grid's three columns each get min-h-0 so they can shrink below
  // content size, and the two rails scroll internally while the viewer
  // stays fixed. (st-fl4)
  return (
    <div
      data-testid="detail-root"
      className="flex flex-col min-[1200px]:h-[calc(100vh-38px)]"
    >
      <DetailHeader title={model.title} modelPath={model.modelPath} />
      <div
        className={clsx(
          "grid flex-1 min-h-0 grid-cols-1 min-[1200px]:grid-rows-[1fr]",
          leftRailCollapsed
            ? "min-[1200px]:grid-cols-[32px_1fr_360px]"
            : "min-[1200px]:grid-cols-[240px_1fr_360px]",
        )}
      >
        <aside
          data-testid="detail-left-col"
          className="min-h-0 border-b border-line bg-panel min-[1200px]:overflow-y-auto min-[1200px]:border-b-0 min-[1200px]:border-r"
        >
          <DetailLeftRail
            modelPath={model.modelPath}
            history={render.history}
            state={render.state}
            warnings={model.warnings}
            accessories={accessories}
            collapsed={leftRailCollapsed}
            onToggleCollapsed={() => setLeftRailCollapsed((c) => !c)}
            mobileOpen={mobileMetadataOpen}
            onToggleMobileOpen={() => setMobileMetadataOpen((o) => !o)}
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
            presets={detail.allPresets}
            activePresetId={detail.state.activePresetId}
            modified={detail.state.modified}
            onLoadPreset={detail.loadPreset}
            onDeletePreset={detail.deleteUserPreset}
            onSavePreset={detail.saveAsPreset}
            saveRowOpen={saveRowOpen}
            setSaveRowOpen={setSaveRowOpen}
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
  accessories,
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onToggleMobileOpen,
}: {
  modelPath: string;
  history: RenderResult[];
  state: RenderState;
  warnings: string[];
  accessories: DetailPageAccessory[];
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onToggleMobileOpen: () => void;
}) {
  // The rail has THREE rendering modes that switch at the 1200px
  // breakpoint:
  //   • mobile (<1200px): single disclosure row above the viewer that
  //     expands to the full content. Default closed (st-yxj).
  //   • desktop collapsed (≥1200px, `collapsed=true`): 32px-wide
  //     column with a chevron-right button.
  //   • desktop expanded (≥1200px, `collapsed=false`): full-width
  //     content with a chevron-left collapse button at the top.
  //
  // The mobile disclosure and the desktop collapse are orthogonal —
  // one viewport's state never affects the other.
  return (
    <>
      {/* Mobile disclosure */}
      <div className="min-[1200px]:hidden">
        <MetadataMobileDisclosure
          history={history}
          warnings={warnings}
          accessories={accessories}
          open={mobileOpen}
          onToggle={onToggleMobileOpen}
        >
          <DetailLeftRailContent
            modelPath={modelPath}
            history={history}
            state={state}
            warnings={warnings}
            accessories={accessories}
          />
        </MetadataMobileDisclosure>
      </div>
      {/* Desktop ≥1200px */}
      {collapsed ? (
        <div
          data-testid="detail-left-rail-collapsed"
          className="hidden min-[1200px]:flex min-[1200px]:flex-col min-[1200px]:items-center min-[1200px]:pt-10"
        >
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label="Expand left rail"
            title="Expand metadata (log, warnings, source)"
            className="inline-flex h-24 w-24 items-center justify-center rounded-3 border border-line bg-panel2 text-text-dim hover:bg-panel-hi hover:text-text"
          >
            <ChevronRightIcon />
          </button>
        </div>
      ) : (
        <div className="hidden min-[1200px]:block">
          <DetailLeftRailContent
            modelPath={modelPath}
            history={history}
            state={state}
            warnings={warnings}
            accessories={accessories}
            onCollapse={onToggleCollapsed}
          />
        </div>
      )}
    </>
  );
}

// Mobile-only disclosure header that summarises the metadata pane in
// one line and opens to the full content on tap. Uses a native
// <details> + <summary> for keyboard/AT support and zero dependency
// cost. Persisted-open state lives one level up via `mobileOpen`.
function MetadataMobileDisclosure({
  history,
  warnings,
  accessories,
  open,
  onToggle,
  children,
}: {
  history: RenderResult[];
  warnings: string[];
  accessories: DetailPageAccessory[];
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const accessorySegment =
    accessories.length > 0
      ? ` · ${accessories.length} accessor${accessories.length === 1 ? "y" : "ies"}`
      : "";
  const summary = `Metadata · ${history.length} render${history.length === 1 ? "" : "s"} · ${
    warnings.length > 0 ? `${warnings.length} warning${warnings.length === 1 ? "" : "s"}` : "clean"
  }${accessorySegment}`;
  return (
    <details
      data-testid="metadata-mobile-disclosure"
      open={open}
      onToggle={(e) => {
        // Sync the persisted state with the native <details> open
        // attribute. React's controlled <details> is awkward; we
        // toggle the parent's flag whenever the element's open state
        // doesn't match.
        const nextOpen = (e.currentTarget as HTMLDetailsElement).open;
        if (nextOpen !== open) onToggle();
      }}
    >
      <summary
        className={clsx(
          "flex cursor-pointer items-center gap-8 border-b border-line bg-panel px-12 py-8",
          "font-mono text-10 uppercase tracking-wide text-text-dim",
          "list-none [&::-webkit-details-marker]:hidden",
          "hover:text-text",
        )}
      >
        <span
          aria-hidden="true"
          className={clsx(
            "inline-block transition-transform",
            open ? "rotate-90" : "rotate-0",
          )}
        >
          ▸
        </span>
        <span>{summary}</span>
      </summary>
      {children}
    </details>
  );
}

function DetailLeftRailContent({
  modelPath,
  history,
  state,
  warnings,
  accessories,
  onCollapse,
}: {
  modelPath: string;
  history: RenderResult[];
  state: RenderState;
  warnings: string[];
  accessories: DetailPageAccessory[];
  onCollapse?: () => void;
}) {
  return (
    <div data-testid="detail-left-rail-content" className="p-10">
      {onCollapse && (
        <div className="mb-8 hidden justify-end min-[1200px]:flex">
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse left rail"
            title="Collapse metadata"
            className="inline-flex h-20 w-20 items-center justify-center rounded-3 border border-line bg-panel2 text-text-dim hover:bg-panel-hi hover:text-text"
          >
            <ChevronLeftIcon />
          </button>
        </div>
      )}
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

      <AccessoriesSection accessories={accessories} />
    </div>
  );
}

function DownloadButton({
  modelPath,
  values,
  canDownload,
  registerHandler,
}: {
  modelPath: string;
  values: Record<string, ParamValue>;
  canDownload: boolean;
  registerHandler: (fn: () => void) => void;
}) {
  const [exportState, setExportState] = useState<ExportState>({ kind: "idle" });

  const handleDownload = useCallback(async () => {
    if (!canDownload) return;
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
  }, [canDownload, modelPath, values]);

  // Register the latest handler so the ⌘E shortcut in DetailPage has a
  // stable reference. Avoids threading a ref down through props.
  useEffect(() => {
    registerHandler(handleDownload);
  }, [handleDownload, registerHandler]);

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

function ChevronRightIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

function ChevronLeftIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}
