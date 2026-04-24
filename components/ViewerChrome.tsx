"use client";

// Viewer chrome: grid overlay, axes indicator, view-preset tabs, and
// the 36px stat strip. Hosts the StlViewer as an absolute-positioned
// sibling so overlays can sit on top without breaking the viewer's
// ResizeObserver.
//
// Keyboard: 1/2/3 pick camera preset; G toggles grid; D toggles dim
// labels; F enters fullscreen; R resets camera; Enter fires the first
// render from idle. All routed through `useShortcut` with a shared
// `focusInViewer && modal.kind === "none"` gate — input rail typing
// doesn't fire viewer keys, and any open modal parks all of them. (st-1j9)

import clsx from "clsx";
import { useCallback, useEffect, useRef, useState } from "react";
import StlViewer, { type StlViewerHandle } from "./StlViewer";
import { Modal } from "./Modal";
import type { CameraPreset } from "@/hooks/useDetailState";
import type { RenderError, RenderResult, RenderState } from "@/hooks/useRenderer";
import { useShortcut } from "@/hooks/useShortcut";
import { useUI } from "@/contexts/UIContext";

interface Props {
  state: RenderState;
  camera: CameraPreset;
  showGrid: boolean;
  showDims: boolean;
  setCamera: (c: CameraPreset) => void;
  toggleGrid: () => void;
  toggleDims: () => void;
  onRefresh: () => void;
  downloadSlot?: React.ReactNode;
  /**
   * Ring buffer of recent successful renders, most-recent first. When
   * an error occurs the most recent is kept visible (dimmed) behind
   * the error strip.
   */
  history?: RenderResult[];
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
  onRefresh,
  downloadSlot,
  history = [],
}: Props) {
  const sectionRef = useRef<HTMLElement>(null);
  const viewerRef = useRef<StlViewerHandle>(null);
  const [focusInViewer, setFocusInViewer] = useState(false);
  const { modal, dispatch } = useUI();

  const lastGood = state.kind === "error" ? history[0] : null;

  const chooseCamera = useCallback(
    (preset: CameraPreset) => {
      setCamera(preset);
      viewerRef.current?.setCameraPreset(preset);
    },
    [setCamera],
  );

  const resetCamera = useCallback(() => {
    viewerRef.current?.resetCamera();
  }, []);

  // Viewer shortcuts are gated on (a) no modal open and (b) focus
  // inside the viewer section. The focus gate avoids the "G fires
  // while typing into a param input" class of bug.
  const gate = modal.kind === "none" && focusInViewer;

  useShortcut("1", () => chooseCamera("top"), { enabled: gate });
  useShortcut("2", () => chooseCamera("front"), { enabled: gate });
  useShortcut("3", () => chooseCamera("iso"), { enabled: gate });
  useShortcut("g", toggleGrid, { enabled: gate });
  useShortcut("d", toggleDims, { enabled: gate });
  useShortcut("r", resetCamera, { enabled: gate });
  useShortcut("f", () => toggleFullscreen(sectionRef.current), {
    enabled: gate,
  });
  // Enter on idle/error kicks off the first render. Unlike the other
  // viewer keys, this doesn't require focusInViewer — the useShortcut
  // input-field guard already keeps Enter-in-a-param-input quiet, and
  // demanding a focus hand-off before the user can trigger the first
  // render is hostile (the viewer has nothing to focus at idle). The
  // guard against in-progress renders still applies via the state
  // check. (st-3lc relaxed gate to beat a hydration race that tight
  // focus→Enter sequences were losing after the phase-3b bundle bump.)
  useShortcut("Enter", onRefresh, {
    enabled:
      modal.kind === "none" &&
      (state.kind === "idle" || state.kind === "error"),
  });

  // Escape closes the error-log modal. UIContext is the arbiter —
  // the shortcut only fires when that modal is the current one, so
  // the palette's own Escape (landed in 3b) won't collide.
  useShortcut(
    "Escape",
    () => dispatch({ type: "close" }),
    { enabled: modal.kind === "errorLog" },
  );

  // Close the log modal whenever the error clears (render succeeded
  // or state transitioned back to loading/idle).
  useEffect(() => {
    if (state.kind !== "error" && modal.kind === "errorLog") {
      dispatch({ type: "close" });
    }
  }, [state.kind, modal.kind, dispatch]);

  return (
    <section
      ref={sectionRef}
      tabIndex={0}
      onFocus={() => setFocusInViewer(true)}
      onBlur={(e) => {
        // Blur fires when focus moves to a nested child too — only
        // flip the gate off when focus actually leaves the section.
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
          setFocusInViewer(false);
        }
      }}
      aria-label="3D preview"
      className="relative flex h-full flex-col bg-panel2 focus:outline-none"
    >
      <div className="relative flex-1 min-h-[480px] min-[1200px]:min-h-0">
        {/* Grid paints first so the model occludes it. StlViewer's
            canvas clears with alpha=0 so the grid shows through where
            the model doesn't cover. (st-lpt) */}
        {showGrid && <GridOverlay />}

        {state.kind === "ready" && <StlViewer ref={viewerRef} stl={state.result.stlBytes} />}
        {state.kind === "loading" && (
          <>
            <ViewerPlaceholder>rendering…</ViewerPlaceholder>
            <LoadingProgressBar />
          </>
        )}
        {state.kind === "idle" && (
          <ViewerPlaceholder>
            <div className="flex flex-col items-center gap-6">
              <div>no render yet</div>
              <kbd
                data-testid="press-enter-hint"
                className="rounded-3 border border-line bg-panel2 px-5 py-1 font-mono text-10 text-text-dim"
              >
                press ⏎ to render
              </kbd>
            </div>
          </ViewerPlaceholder>
        )}
        {state.kind === "error" && lastGood && (
          <>
            <StlViewer ref={viewerRef} stl={lastGood.stlBytes} />
            <div className="pointer-events-none absolute inset-0 bg-bg/70" />
          </>
        )}
        {state.kind === "error" && !lastGood && (
          <ViewerPlaceholder tone="error">
            <div className="font-semibold">render failed</div>
          </ViewerPlaceholder>
        )}

        <AxesIndicator camera={camera} />

        <ViewPresetTabs camera={camera} onPick={chooseCamera} />

        {showDims && <DimsPlaceholder />}

        <ErrorStrip
          error={state.kind === "error" ? state.error : null}
          onViewLog={() => {
            if (state.kind === "error") {
              dispatch({ type: "open", modal: { kind: "errorLog", log: state.error.log } });
            }
          }}
        />
      </div>
      <StatStrip state={state} downloadSlot={downloadSlot} />
      <ErrorLogModal />
    </section>
  );
}

function ErrorLogModal() {
  const { modal, dispatch } = useUI();
  const open = modal.kind === "errorLog";
  const log = modal.kind === "errorLog" ? modal.log : "";
  return (
    <Modal
      open={open}
      onClose={() => dispatch({ type: "close" })}
      label="Render error log"
      className="w-full max-w-[720px]"
    >
      <div data-testid="error-log-modal">
        <div className="flex items-center justify-between border-b border-line px-14 py-8">
          <span className="font-mono text-11 uppercase tracking-wide text-text-dim">
            Render log
          </span>
          <button
            type="button"
            onClick={() => dispatch({ type: "close" })}
            aria-label="Close render log"
            className="font-mono text-11 text-text-dim hover:text-text"
          >
            ✕
          </button>
        </div>
        <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap px-14 py-12 font-mono text-11 text-text">
          {log || "(empty)"}
        </pre>
      </div>
    </Modal>
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
      data-testid="viewer-grid"
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
  if (state.kind === "loading") {
    return (
      <StatStripShell downloadSlot={downloadSlot}>
        <span data-testid="stat-strip-status" className="text-text-dim">
          compiling…
        </span>
      </StatStripShell>
    );
  }
  if (state.kind === "idle") {
    return (
      <StatStripShell downloadSlot={downloadSlot}>
        <span data-testid="stat-strip-status" className="text-text-mute">
          press ⏎ to render
        </span>
      </StatStripShell>
    );
  }
  if (state.kind === "error") {
    return (
      <StatStripShell downloadSlot={downloadSlot}>
        <span data-testid="stat-strip-status" className="text-red">
          error
        </span>
      </StatStripShell>
    );
  }
  const { result } = state;
  const dims = `${fmt1(result.dimensions.x)} × ${fmt1(result.dimensions.y)} × ${fmt1(result.dimensions.z)} mm`;
  const kb = (result.stlBytes.byteLength / 1024).toFixed(1);
  return (
    <StatStripShell downloadSlot={downloadSlot}>
      <span data-testid="stat-strip-dimensions">
        <span className="text-text-mute">DIM </span>
        <span className="text-text">{dims}</span>
      </span>
      <Stat label="TRI" value={result.triCount.toLocaleString()} />
      <Stat label="MS" value={result.ms.toFixed(0)} />
      <Stat label="KB" value={kb} />
    </StatStripShell>
  );
}

function StatStripShell({
  children,
  downloadSlot,
}: {
  children: React.ReactNode;
  downloadSlot?: React.ReactNode;
}) {
  return (
    <div
      data-testid="stat-strip"
      className="flex h-36 items-center gap-18 border-t border-line bg-panel px-12 font-mono text-10 text-text-dim"
    >
      {children}
      <span className="flex-1" />
      {downloadSlot}
    </div>
  );
}

function LoadingProgressBar() {
  return (
    <div
      data-testid="loading-progress"
      className="pointer-events-none absolute inset-x-0 bottom-0 h-2 overflow-hidden bg-panel"
    >
      <div
        className="h-full w-1/3 bg-accent"
        style={{ animation: "caliper-slide 1.2s ease-in-out infinite" }}
      />
    </div>
  );
}

function fmt1(n: number): string {
  return n.toFixed(1);
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-4">
      <span className="text-text-mute">{label}</span>
      <span className="text-text">{value}</span>
    </div>
  );
}

function ErrorStrip({
  error,
  onViewLog,
}: {
  error: RenderError | null;
  onViewLog: () => void;
}) {
  const shown = error != null;
  return (
    <div
      role="alert"
      data-testid="error-strip"
      aria-hidden={!shown}
      className={clsx(
        "pointer-events-none absolute inset-x-0 bottom-0 z-10",
        "flex items-center gap-12 border-t border-red bg-red-tint px-12 py-8",
        "font-mono text-11 transition-transform duration-200 ease-out",
        shown ? "translate-y-0" : "translate-y-full",
      )}
    >
      {shown && (
        <>
          <span className="shrink-0 font-semibold text-red">error</span>
          {error.line != null && (
            <span className="shrink-0 text-text-dim">line {error.line}</span>
          )}
          <span className="flex-1 truncate text-text">{error.message}</span>
          <button
            type="button"
            onClick={onViewLog}
            className="pointer-events-auto shrink-0 text-accent hover:underline"
          >
            view full log
          </button>
        </>
      )}
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
