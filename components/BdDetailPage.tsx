"use client";

// Detail view for build123d (engine="build123d") models.
//
// P1 (pst-0um9) shipped a presets-only view: a baked GLB per preset, an
// STL download of that bake, and a read-only param table. P2c (pst-qbas)
// turns it live:
//   • Params are EDITABLE via the shared ParamRail (same control set as
//     the SCAD viewer). useDetailState drives param/preset/modified state.
//   • Selecting a preset loads its INSTANT baked GLB (via /api/bd-asset) —
//     no service call. Page-load and preset views therefore cost nothing.
//   • Changing any param marks the view stale. An explicit Update/Enter
//     action (manual refresh, matching the SCAD pst-vfp decision — NOT a
//     render on every keystroke) calls /api/bd-render for a fresh live
//     render of the current params. build123d can't render in the browser,
//     so there is no WASM fallback: a cold/slow service shows a clear
//     "rendering…" state and a disabled/unreachable one a friendly error.
//   • STL Download uses the CURRENT live params via /api/bd-render?format=
//     stl, so a tweaked download reflects the tweak, not just the preset.

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import clsx from "clsx";
import GlbViewer, { type GlbBbox } from "./GlbViewer";
import { AxesIndicator } from "./AxesIndicator";
import { ParamRail } from "./ParamRail";
import type { CameraAxes } from "./StlViewer";
import { paramsEqual, useDetailState } from "@/hooks/useDetailState";
import { useBdRenderer } from "@/hooks/useBdRenderer";
import type { Param, ParamValue, Preset } from "@/lib/scad-params/parse";

export interface BdDetailPageModel {
  slug: string;
  title: string;
  blurb: string;
  params: Param[];
  presets: Preset[];
}

function assetUrl(slug: string, presetId: string, format: "glb" | "stl"): string {
  return `/api/bd-asset/${slug}/${presetId}?format=${format}`;
}

export default function BdDetailPage({ model }: { model: BdDetailPageModel }) {
  const detail = useDetailState({
    params: model.params,
    stockPresets: model.presets,
    slug: model.slug,
  });
  const bd = useBdRenderer(model.slug);

  const [viewerError, setViewerError] = useState<string | null>(null);
  // Loaded GLB extents, surfaced for the e2e orientation assertion and
  // shown in the stat strip. size = [x, y, z] in the GLB's units.
  const [bbox, setBbox] = useState<GlbBbox | null>(null);
  // Live camera orientation from the GLB viewer, feeding the shared
  // orientation compass. null until the first onCameraChange fires.
  const [axes, setAxes] = useState<CameraAxes | null>(null);
  // The GLB currently driven into the viewer from a successful live
  // render. null = show the baked preset GLB. Set only on a render
  // success (not during loading/error) so the last good geometry stays
  // on screen while the next render is in flight — mirrors the SCAD
  // viewer keeping the previous mesh during a re-render.
  const [liveGlb, setLiveGlb] = useState<{ bytes: Uint8Array; seq: number } | null>(
    null,
  );

  const activePresetId = detail.state.activePresetId ?? model.presets[0]?.id ?? "";
  const activePreset =
    model.presets.find((p) => p.id === activePresetId) ?? model.presets[0];

  // Land on the first preset on mount so the baked GLB shows immediately
  // and the controls reflect that preset's values. Runs once.
  useEffect(() => {
    if (detail.state.activePresetId === null && model.presets[0]) {
      detail.loadPreset(model.presets[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Promote a completed render into the viewer.
  useEffect(() => {
    if (bd.state.kind === "ready") {
      setLiveGlb({ bytes: bd.state.glb, seq: bd.state.seq });
    }
  }, [bd.state]);

  const showingLive = liveGlb !== null;

  // Staleness: does the on-screen geometry match the live controls?
  //   • Showing a live render → compare against its snapshot.
  //   • Showing a baked preset → drift from the preset (modified) is stale.
  const stale = showingLive
    ? bd.renderedValues === null ||
      !paramsEqual(detail.state.params, bd.renderedValues, model.params)
    : detail.state.modified;

  const selectPreset = useCallback(
    (id: string) => {
      detail.loadPreset(id);
      // Back to the instant baked view — drop any live render and cancel
      // an in-flight one so a preset click never costs a service call.
      bd.reset();
      setLiveGlb(null);
      setViewerError(null);
    },
    [detail, bd],
  );

  const update = useCallback(() => {
    if (!stale && bd.state.kind !== "error") return;
    setViewerError(null);
    bd.refresh(detail.state.params);
  }, [stale, bd, detail.state.params]);

  const onLoaded = useCallback((b: GlbBbox) => {
    setViewerError(null);
    setBbox(b);
    // Orientation guard: warn only on a gross lay-down. A depth (Z) that
    // *dwarfs* the height (Y) means the Y-up transform was likely applied
    // twice, toppling the model. See the P1 note — near-cubic holders
    // legitimately have depth slightly over height, so flag only a wide
    // margin. (The e2e spec pins the exact upright envelope.)
    const [, y, z] = b.size;
    if (z > y * 1.5) {
      console.warn(
        `GLB orientation looks wrong for ${model.slug}: depth ${z.toFixed(4)} ` +
          `far exceeds height ${y.toFixed(4)} — is the Y-up transform being ` +
          `applied twice?`,
      );
    }
  }, [model.slug]);

  const onError = useCallback((message: string) => {
    setViewerError(message);
  }, []);

  if (!activePreset) {
    // A manifest entry with no presets can't be baked or shown. P1b's
    // validator forbids this for app-listed models, but fail visibly.
    return (
      <div className="p-24 text-13 text-text-dim">
        <Link href="/" className="text-11 text-text-dim hover:text-text">
          ← all models
        </Link>
        <p className="mt-12">{model.title} has no presets to display.</p>
      </div>
    );
  }

  const renderState = bd.state.kind;

  return (
    <div
      data-testid="bd-detail-root"
      data-engine="build123d"
      data-bd-render-state={renderState}
      data-bd-source={showingLive ? "live" : "preset"}
      data-bd-stale={stale ? "true" : "false"}
      className="flex flex-col min-[1200px]:h-[calc(100vh-38px)]"
    >
      {/* Header */}
      <div className="flex items-baseline gap-12 border-b border-line bg-panel px-12 py-8">
        <Link
          href="/"
          className="text-11 text-text-dim no-underline hover:text-text"
        >
          ← all models
        </Link>
        <h1 className="m-0 text-14 font-semibold text-text">{model.title}</h1>
        <code className="font-mono text-10 text-text-mute">
          {model.slug.replaceAll("-", "_")}.py (build123d)
        </code>
      </div>

      <div className="grid flex-1 min-h-0 grid-cols-1 min-[1200px]:grid-cols-[1fr_360px] min-[1200px]:grid-rows-[1fr]">
        {/* Viewer */}
        <div className="relative min-h-[360px] bg-panel2 min-[1200px]:min-h-0">
          <GlbViewer
            key={
              showingLive
                ? `live-${liveGlb!.seq}`
                : `preset-${activePreset.id}`
            }
            url={showingLive ? undefined : assetUrl(model.slug, activePreset.id, "glb")}
            bytes={showingLive ? liveGlb!.bytes : undefined}
            onLoaded={onLoaded}
            onError={onError}
            onCameraChange={setAxes}
          />
          {/* Orientation compass — same component as the SCAD viewer.
              Offset up to clear the bottom stat strip below. */}
          <AxesIndicator axes={axes} className="bottom-40 left-12" />

          {/* Stale callout: params drifted from the shown geometry. An
              explicit Update triggers the (manual) live render. */}
          {stale && renderState !== "loading" && (
            <div
              data-testid="bd-stale-notice"
              className="absolute inset-x-0 top-0 m-8 flex items-center justify-between gap-8 rounded-3 border border-accent-line bg-panel/95 px-10 py-6 text-11 text-text"
            >
              <span>Parameters changed — preview is out of date.</span>
              <button
                type="button"
                data-testid="bd-update-render"
                onClick={update}
                className="rounded-3 border border-accent-line bg-accent px-8 py-3 font-semibold text-accent-ink hover:opacity-90"
              >
                Update
              </button>
            </div>
          )}

          {/* Warming / rendering state — build123d renders in a scale-to-
              zero service, so a cold start can take seconds. Say so
              explicitly rather than showing a silent spinner. */}
          {renderState === "loading" && (
            <div
              data-testid="bd-render-warming"
              className="absolute inset-x-0 top-0 m-8 rounded-3 border border-accent-line bg-panel/95 px-10 py-6 text-11 text-text"
            >
              Rendering… the build123d service may be warming up from cold.
            </div>
          )}

          {/* Live-render error — no WASM fallback, so this is terminal for
              the attempt; the controls stay editable and Update retries. */}
          {renderState === "error" && (
            <div
              data-testid="bd-render-error"
              className="absolute inset-x-0 top-0 m-8 flex items-center justify-between gap-8 rounded-3 border border-red/40 bg-panel px-10 py-6 text-11 text-red"
            >
              <span>
                {bd.state.kind === "error" ? bd.state.message : "Render failed."}
              </span>
              <button
                type="button"
                data-testid="bd-render-retry"
                onClick={update}
                className="rounded-3 border border-red/40 bg-panel2 px-8 py-3 font-semibold text-red hover:opacity-90"
              >
                Retry
              </button>
            </div>
          )}

          {viewerError && renderState !== "error" && (
            <div
              data-testid="bd-viewer-error"
              className="absolute inset-x-0 top-0 m-8 rounded-3 border border-red/40 bg-panel px-10 py-6 text-11 text-red"
            >
              Couldn&apos;t load preview: {viewerError}
            </div>
          )}

          {/* Stat strip — mirrors the SCAD viewer's 36px footer. */}
          <div className="absolute inset-x-0 bottom-0 flex items-center gap-12 border-t border-line bg-panel/90 px-12 py-6 font-mono text-10 text-text-mute">
            <span data-testid="bd-preset-label">
              {showingLive ? "live render" : activePreset.label}
            </span>
            {bbox && (
              <span
                data-testid="bd-glb-size"
                data-glb-size={bbox.size.map((n) => n.toFixed(4)).join(",")}
              >
                bbox {bbox.size.map((n) => (n * 1000).toFixed(0)).join(" × ")} mm
              </span>
            )}
          </div>
        </div>

        {/* Right rail: presets + download + editable params */}
        <aside
          data-testid="bd-detail-rail"
          className="min-h-0 border-t border-line bg-panel p-12 min-[1200px]:overflow-y-auto min-[1200px]:border-l min-[1200px]:border-t-0"
        >
          <p className="m-0 text-12 text-text-dim">{model.blurb}</p>

          {/* Preset picker — each loads its baked GLB with no service call. */}
          <div className="mt-16 font-mono text-10 uppercase tracking-wide text-text-mute">
            Presets
          </div>
          <div className="mt-6 flex flex-col gap-4" role="listbox" aria-label="Presets">
            {model.presets.map((p) => {
              const active = !showingLive && p.id === activePreset.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  data-testid={`bd-preset-${p.id}`}
                  onClick={() => selectPreset(p.id)}
                  className={clsx(
                    "flex flex-col items-start rounded-3 border px-10 py-6 text-left",
                    active
                      ? "border-accent-line bg-panel-hi text-text"
                      : "border-line bg-panel2 text-text-dim hover:bg-panel-hi hover:text-text",
                  )}
                >
                  <span className="text-12 font-semibold">{p.label}</span>
                  <span className="font-mono text-10 text-text-mute">{p.id}</span>
                </button>
              );
            })}
          </div>

          {/* Download — always the CURRENT live params via /api/bd-render. */}
          <BdDownloadStl slug={model.slug} values={detail.state.params} />

          {/* Editable params — shared control set with the SCAD viewer. */}
          <div className="mt-18 font-mono text-10 uppercase tracking-wide text-text-mute">
            Parameters
          </div>
          <p className="mt-2 text-10 text-text-mute">
            Edit values, then Update the preview. Changes render on the
            build123d service — presets stay instant.
          </p>
          <div className="mt-6 border-t border-line">
            <ParamRail
              params={model.params}
              values={detail.state.params}
              onChange={detail.setParam}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}

type DownloadState =
  | { kind: "idle" }
  | { kind: "exporting" }
  | { kind: "error"; message: string };

// STL download for build123d: always renders the CURRENT live params via
// /api/bd-render?format=stl (AC6) — a tweaked download reflects the tweak,
// not just the baked preset. No WASM fallback, so a disabled/unreachable
// service surfaces a friendly inline error.
function BdDownloadStl({
  slug,
  values,
}: {
  slug: string;
  values: Record<string, ParamValue>;
}) {
  const [state, setState] = useState<DownloadState>({ kind: "idle" });

  const download = useCallback(async () => {
    setState({ kind: "exporting" });
    try {
      const res = await fetch("/api/bd-render?format=stl", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ slug, params: values }),
      });
      if (!res.ok) {
        let message =
          res.status === 503
            ? "Live rendering is currently unavailable."
            : `Export failed (HTTP ${res.status}).`;
        try {
          const body = await res.json();
          if (typeof body?.error === "string") message = body.error;
        } catch {
          /* keep message */
        }
        setState({ kind: "error", message });
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${slug}.stl`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setState({ kind: "idle" });
    } catch (e) {
      setState({
        kind: "error",
        message: e instanceof Error ? e.message : "network error",
      });
    }
  }, [slug, values]);

  return (
    <div className="mt-16">
      <button
        type="button"
        data-testid="bd-download-stl"
        onClick={download}
        disabled={state.kind === "exporting"}
        className={clsx(
          "inline-flex w-full items-center justify-center rounded-3",
          "border border-accent-line bg-accent px-8 py-6",
          "font-semibold text-accent-ink no-underline hover:opacity-90",
          "disabled:cursor-wait disabled:opacity-60",
        )}
      >
        {state.kind === "exporting" ? "Preparing STL…" : "Download STL"}
      </button>
      {state.kind === "error" && (
        <p
          data-testid="bd-download-error"
          className="mt-4 text-10 text-red"
        >
          {state.message}
        </p>
      )}
    </div>
  );
}
