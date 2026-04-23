"use client";

// Viewer chrome: grid overlay, axes indicator, view-preset tabs, and
// the 36px stat strip. Hosts the StlViewer as an absolute-positioned
// sibling so overlays can sit on top without breaking the viewer's
// ResizeObserver.
//
// Keyboard: 1/2/3 pick camera preset; G toggles grid; D toggles dim
// labels (phase 2 renders them); F enters fullscreen on the viewer
// container (Fullscreen API). No R-reset — phase 3 global map owns it.

import clsx from "clsx";
import { useCallback, useEffect, useRef } from "react";
import StlViewer, { type StlViewerHandle } from "./StlViewer";
import type { CameraPreset } from "@/hooks/useDetailState";
import type { RenderState } from "@/hooks/useRenderer";

interface Props {
  state: RenderState;
  camera: CameraPreset;
  showGrid: boolean;
  showDims: boolean;
  setCamera: (c: CameraPreset) => void;
  toggleGrid: () => void;
  toggleDims: () => void;
  downloadSlot?: React.ReactNode;
}

const PRESETS: readonly CameraPreset[] = ["top", "front", "iso"] as const;

export function ViewerChrome({
  state,
  camera,
  showGrid,
  showDims,
  setCamera,
  toggleGrid,
  toggleDims,
  downloadSlot,
}: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const viewerContainerRef = useRef<HTMLDivElement>(null);

  // Drive the StlViewer camera via the __stlViewer DOM debug handle —
  // 1c extends it with setCameraPreset so tabs and the number-key
  // keymap both share the same path. A phase-2 follow-up replaces this
  // with a typed useImperativeHandle.
  const applyCameraToCanvas = useCallback((preset: CameraPreset) => {
    const canvas = viewerContainerRef.current?.querySelector("canvas");
    const handle = (canvas as unknown as { __stlViewer?: StlViewerHandle } | null)
      ?.__stlViewer;
    handle?.setCameraPreset(preset);
  }, []);

  const chooseCamera = useCallback(
    (preset: CameraPreset) => {
      setCamera(preset);
      applyCameraToCanvas(preset);
    },
    [setCamera, applyCameraToCanvas],
  );

  function handleKeyDown(e: React.KeyboardEvent<HTMLElement>) {
    // Ignore keys when the event target is a form field — prevents
    // "G" from toggling the grid while the user types into a param
    // input. All row inputs/buttons/selects should absorb their own
    // keys before bubbling up here.
    const tag = (e.target as HTMLElement).tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (e.key === "1") chooseCamera("top");
    else if (e.key === "2") chooseCamera("front");
    else if (e.key === "3") chooseCamera("iso");
    else if (e.key === "g" || e.key === "G") toggleGrid();
    else if (e.key === "d" || e.key === "D") toggleDims();
    else if (e.key === "f" || e.key === "F") toggleFullscreen(sectionRef.current);
    else return;
    e.preventDefault();
  }

  return (
    <section
      ref={sectionRef}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label="3D preview"
      className="relative flex flex-col bg-panel2 focus:outline-none"
    >
      <div ref={viewerContainerRef} className="relative min-h-[480px] flex-1">
        {state.kind === "ready" && <StlViewer stl={state.result.stlBytes} />}
        {state.kind === "loading" && (
          <ViewerPlaceholder>rendering…</ViewerPlaceholder>
        )}
        {state.kind === "idle" && <ViewerPlaceholder>idle</ViewerPlaceholder>}
        {state.kind === "error" && (
          <ViewerPlaceholder tone="error">
            <div className="font-semibold">render failed</div>
            <pre className="mt-8 max-w-[560px] overflow-auto whitespace-pre-wrap font-mono text-11">
              {state.error.message}
            </pre>
          </ViewerPlaceholder>
        )}

        {showGrid && <GridOverlay />}
        <AxesIndicator camera={camera} />

        <ViewPresetTabs camera={camera} onPick={chooseCamera} />

        {showDims && <DimsPlaceholder />}
      </div>
      <StatStrip state={state} downloadSlot={downloadSlot} />
    </section>
  );
}

function ViewerPlaceholder({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: "error";
}) {
  return (
    <div
      className={clsx(
        "flex h-full items-center justify-center",
        tone === "error" ? "text-red" : "text-text-dim",
      )}
    >
      <div className="flex flex-col items-center">{children}</div>
    </div>
  );
}

function GridOverlay() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      <defs>
        <pattern
          id="caliper-grid-fine"
          width="10"
          height="10"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 10 0 L 0 0 0 10"
            className="stroke-line-soft"
            fill="none"
            strokeWidth="0.5"
          />
        </pattern>
        <pattern
          id="caliper-grid-coarse"
          width="50"
          height="50"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 50 0 L 0 0 0 50"
            className="stroke-line"
            fill="none"
            strokeWidth="1"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#caliper-grid-fine)" />
      <rect width="100%" height="100%" fill="url(#caliper-grid-coarse)" />
    </svg>
  );
}

function AxesIndicator({ camera }: { camera: CameraPreset }) {
  // Hint the current view by rotating the axes tripod's wrapper. The
  // 3D axes are placeholder glyphs — the actual camera orientation
  // lives in three.js. Phase 2 can switch to a live-computed gizmo.
  const rot =
    camera === "top" ? "rotate-90" : camera === "front" ? "-rotate-12" : "rotate-0";
  return (
    <div
      className={clsx(
        "pointer-events-none absolute bottom-12 left-12 font-mono text-10 transition-transform",
        rot,
      )}
      aria-label={`camera: ${camera}`}
    >
      <svg width="56" height="56" viewBox="0 0 72 72">
        <line x1="20" y1="52" x2="50" y2="52" className="stroke-red" strokeWidth="1.2" />
        <text x="54" y="55" className="fill-red" fontSize="9">X</text>
        <line x1="20" y1="52" x2="20" y2="22" className="stroke-green" strokeWidth="1.2" />
        <text x="14" y="20" className="fill-green" fontSize="9">Z</text>
        <line x1="20" y1="52" x2="38" y2="64" className="stroke-blue" strokeWidth="1.2" />
        <text x="40" y="68" className="fill-blue" fontSize="9">Y</text>
      </svg>
    </div>
  );
}

function ViewPresetTabs({
  camera,
  onPick,
}: {
  camera: CameraPreset;
  onPick: (c: CameraPreset) => void;
}) {
  return (
    <div className="absolute right-12 top-12 flex gap-2" role="tablist" aria-label="View presets">
      {PRESETS.map((p) => (
        <button
          key={p}
          type="button"
          role="tab"
          aria-selected={camera === p}
          data-preset={p}
          onClick={() => onPick(p)}
          className={clsx(
            "rounded-3 border px-6 py-2 font-mono text-10 uppercase tracking-wide",
            camera === p
              ? "border-accent-line bg-accent-soft text-text"
              : "border-line bg-panel text-text-dim hover:text-text",
          )}
        >
          {p}
        </button>
      ))}
      <button
        type="button"
        onClick={(e) => toggleFullscreen(e.currentTarget.closest("section"))}
        className={clsx(
          "rounded-3 border border-line bg-panel px-6 py-2",
          "font-mono text-10 uppercase tracking-wide text-text-dim hover:text-text",
        )}
        aria-label="Toggle fullscreen viewer"
      >
        full
      </button>
    </div>
  );
}

function DimsPlaceholder() {
  // Phase 2 hooks up the real bounding-box-derived dimension labels.
  // For now, just signal the toggle is alive so `D` feels responsive.
  return (
    <div
      className={clsx(
        "pointer-events-none absolute bottom-12 right-12",
        "rounded-3 border border-line bg-panel px-6 py-2",
        "font-mono text-10 text-text-mute",
      )}
    >
      dims
    </div>
  );
}

function StatStrip({
  state,
  downloadSlot,
}: {
  state: RenderState;
  downloadSlot?: React.ReactNode;
}) {
  const tri = state.kind === "ready" ? state.result.triCount : null;
  const ms = state.kind === "ready" ? state.result.ms.toFixed(0) : null;
  const kb =
    state.kind === "ready"
      ? (state.result.stlBytes.byteLength / 1024).toFixed(1)
      : null;
  return (
    <div className="flex h-36 items-center gap-18 border-t border-line bg-panel px-12 font-mono text-10 text-text-dim">
      <Stat label="TRI" value={tri != null ? tri.toLocaleString() : "—"} />
      <Stat label="MS" value={ms ?? "—"} />
      <Stat label="KB" value={kb ?? "—"} />
      <span className="flex-1" />
      {downloadSlot}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <span className="text-text-mute">{label}</span>
      <span className="text-text">{value}</span>
    </div>
  );
}

function toggleFullscreen(el: Element | null) {
  if (!el) return;
  if (document.fullscreenElement) {
    void document.exitFullscreen();
  } else {
    void (el as HTMLElement).requestFullscreen?.();
  }
}
