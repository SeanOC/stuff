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
import StlViewer, { type CameraAxes, type StlViewerHandle } from "./StlViewer";
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
  // Live camera orientation, updated on every OrbitControls 'change'
  // event via onCameraChange. Drives the axes indicator; the `camera`
  // preset prop is kept for the tab highlight only. (st-oc3)
  const [axes, setAxes] = useState<CameraAxes | null>(null);
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

        {state.kind === "ready" && (
          <StlViewer
            ref={viewerRef}
            stl={state.result.stlBytes}
            onCameraChange={setAxes}
          />
        )}
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
            <StlViewer
              ref={viewerRef}
              stl={lastGood.stlBytes}
              onCameraChange={setAxes}
            />
            <div className="pointer-events-none absolute inset-0 bg-bg/70" />
          </>
        )}
        {state.kind === "error" && !lastGood && (
          <ViewerPlaceholder tone="error">
            <div className="font-semibold">render failed</div>
          </ViewerPlaceholder>
        )}

        <AxesIndicator axes={axes} preset={camera} />

        <div className="absolute right-12 top-12 flex items-center gap-10">
          <ViewPresetTabs camera={camera} onPick={chooseCamera} />
          <FullscreenButton sectionRef={sectionRef} />
        </div>

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

// Axes indicator — bottom-left, 56×56. When the live camera has fired
// at least one onCameraChange (axes != null) the three lines point in
// the screen-space direction of the world X/Y/Z basis vectors. Before
// that (cold mount, before the scene boots), fall back to the preset-
// name-driven static orientation so the indicator isn't blank. (st-oc3)
function AxesIndicator({
  axes,
  preset,
}: {
  axes: CameraAxes | null;
  preset: CameraPreset;
}) {
  // SVG viewBox is 72×72; keep the origin near the bottom-left quadrant
  // (20, 52) to match the previous visual placement within the 56×56
  // frame. Line length R is 22px — slightly longer than the old fixed
  // lines so the labels sit clear of the origin on all orientations.
  const cx = 26;
  const cy = 46;
  const R = 22;
  return (
    <div
      className="pointer-events-none absolute bottom-12 left-12 font-mono text-10"
      aria-label={`camera: ${preset}`}
      data-testid="axes-indicator"
      data-preset={preset}
    >
      <svg width="56" height="56" viewBox="0 0 72 72">
        {axes ? (
          <>
            <AxisLine cx={cx} cy={cy} dir={axes.x} R={R} color="red" label="X" />
            <AxisLine cx={cx} cy={cy} dir={axes.z} R={R} color="green" label="Z" />
            <AxisLine cx={cx} cy={cy} dir={axes.y} R={R} color="blue" label="Y" />
          </>
        ) : (
          <StaticAxes cx={cx} cy={cy} R={R} preset={preset} />
        )}
      </svg>
    </div>
  );
}

function AxisLine({
  cx,
  cy,
  dir,
  R,
  color,
  label,
}: {
  cx: number;
  cy: number;
  dir: [number, number, number];
  R: number;
  color: "red" | "green" | "blue";
  label: string;
}) {
  // dir is in view space: x = screen right, y = screen up (SVG y flips),
  // z = depth. Three.js cameras look down -Z in view space, so positive
  // z points toward the viewer (axis tip out of screen) and negative z
  // points into the scene (axis tip hidden behind). Dim the away-facing
  // axes so the ones extending toward the viewer read as dominant.
  const [dx, dy, dz] = dir;
  const x2 = cx + dx * R;
  const y2 = cy - dy * R;
  const labelX = cx + dx * (R + 6);
  const labelY = cy - dy * (R + 6);
  const opacity = dz < -0.05 ? 0.35 : 1;
  const stroke =
    color === "red"
      ? "stroke-red"
      : color === "green"
        ? "stroke-green"
        : "stroke-blue";
  const fill =
    color === "red"
      ? "fill-red"
      : color === "green"
        ? "fill-green"
        : "fill-blue";
  return (
    <g opacity={opacity} data-axis={label.toLowerCase()}>
      <line
        x1={cx}
        y1={cy}
        x2={x2}
        y2={y2}
        className={stroke}
        strokeWidth="1.2"
        strokeLinecap="round"
      />
      <text
        x={labelX}
        y={labelY}
        className={fill}
        fontSize="9"
        textAnchor="middle"
        dominantBaseline="middle"
      >
        {label}
      </text>
    </g>
  );
}

// Pre-callback fallback. Matches the pre-st-oc3 orientation so the
// indicator isn't blank on a cold SSR paint or between mount and the
// first controls change. Once onCameraChange fires (usually within a
// frame of mount) this is replaced by the live projection.
function StaticAxes({
  cx,
  cy,
  R,
  preset,
}: {
  cx: number;
  cy: number;
  R: number;
  preset: CameraPreset;
}) {
  // Preset-specific hand-drawn placeholder. Angles chosen to roughly
  // match what the live projection lands at for each preset.
  const table: Record<
    CameraPreset,
    { x: [number, number, number]; y: [number, number, number]; z: [number, number, number] }
  > = {
    top: {
      x: [1, 0, 0],
      y: [0, 1, 0],
      z: [0, 0, -1],
    },
    front: {
      x: [1, 0, 0],
      y: [0, 0, 1],
      z: [0, 1, 0],
    },
    iso: {
      x: [0.81, -0.3, -0.5],
      y: [-0.5, -0.3, -0.81],
      z: [0, 0.9, -0.42],
    },
  };
  const t = table[preset];
  return (
    <>
      <AxisLine cx={cx} cy={cy} dir={t.x} R={R} color="red" label="X" />
      <AxisLine cx={cx} cy={cy} dir={t.z} R={R} color="green" label="Z" />
      <AxisLine cx={cx} cy={cy} dir={t.y} R={R} color="blue" label="Y" />
    </>
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
    <div className="flex gap-2" role="tablist" aria-label="View presets">
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
    </div>
  );
}

// Separated from the view-preset pills (st-iz1) because toggling
// fullscreen is a categorically different action from picking a
// camera — the icon + visible gap stop the user reading it as "the
// fourth preset." The icon flips between maximize/minimize based on
// `document.fullscreenElement`, synced through a `fullscreenchange`
// listener so the button also updates when the user presses Esc or
// the F shortcut.
function FullscreenButton({
  sectionRef,
}: {
  sectionRef: React.RefObject<HTMLElement | null>;
}) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const onChange = () => {
      setIsFullscreen(document.fullscreenElement !== null);
    };
    onChange();
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const label = isFullscreen ? "Exit fullscreen" : "Enter fullscreen";
  return (
    <button
      type="button"
      onClick={() => toggleFullscreen(sectionRef.current)}
      className={clsx(
        "inline-flex h-24 w-24 items-center justify-center rounded-3 border",
        isFullscreen
          ? "border-accent-line bg-accent-soft text-accent"
          : "border-line bg-panel text-text-dim hover:bg-panel-hi hover:text-text",
      )}
      aria-label={label}
      title="Fullscreen (F)"
    >
      {isFullscreen ? <MinimizeIcon /> : <MaximizeIcon />}
    </button>
  );
}

function MaximizeIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 3H5a2 2 0 0 0-2 2v3" />
      <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
      <path d="M3 16v3a2 2 0 0 0 2 2h3" />
      <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    </svg>
  );
}

function MinimizeIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M8 3v3a2 2 0 0 1-2 2H3" />
      <path d="M21 8h-3a2 2 0 0 1-2-2V3" />
      <path d="M3 16h3a2 2 0 0 1 2 2v3" />
      <path d="M16 21v-3a2 2 0 0 1 2-2h3" />
    </svg>
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
