"use client";

// Detail view for build123d (engine="build123d") models — the P1 preset
// flow (bead pst-0um9). Deliberately NOT the SCAD DetailPage: there is
// no live WASM preview and no param editing yet. The viewer shows the
// build-time-baked GLB for the selected preset; Download STL streams the
// baked STL. Params are shown read-only with a clear "presets only for
// now" banner so the missing live controls read as intentional.

import Link from "next/link";
import { useCallback, useState } from "react";
import clsx from "clsx";
import GlbViewer, { type GlbBbox } from "./GlbViewer";
import { AxesIndicator } from "./AxesIndicator";
import type { CameraAxes } from "./StlViewer";
import type { Param, Preset } from "@/lib/scad-params/parse";

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
  const [activePresetId, setActivePresetId] = useState(
    model.presets[0]?.id ?? "",
  );
  const [viewerError, setViewerError] = useState<string | null>(null);
  // Loaded GLB extents, surfaced for the e2e orientation assertion and
  // shown in the stat strip. size = [x, y, z] in the GLB's units.
  const [bbox, setBbox] = useState<GlbBbox | null>(null);
  // Live camera orientation from the GLB viewer, feeding the shared
  // orientation compass. null until the first onCameraChange fires (on
  // GLB load), at which point AxesIndicator shows the live projection.
  const [axes, setAxes] = useState<CameraAxes | null>(null);

  const activePreset =
    model.presets.find((p) => p.id === activePresetId) ?? model.presets[0];

  const onLoaded = useCallback((b: GlbBbox) => {
    setViewerError(null);
    setBbox(b);
    // Orientation guard: warn only on a gross lay-down. A depth (Z) that
    // *dwarfs* the height (Y) means the Y-up transform was likely applied
    // twice, toppling the model. We can't assert "Y is tallest" generically:
    // a near-cubic holder legitimately has depth slightly over height (the
    // spray-can's ~64mm back-plate depth vs 60mm collar). So flag only when
    // depth exceeds height by a wide margin, which no upright holder does.
    // (The e2e spec pins the exact envelope via data-glb-size below.)
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
        <p className="mt-12">
          {model.title} has no presets to display.
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="bd-detail-root"
      data-engine="build123d"
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
            key={`${model.slug}/${activePreset.id}`}
            url={assetUrl(model.slug, activePreset.id, "glb")}
            onLoaded={onLoaded}
            onError={onError}
            onCameraChange={setAxes}
          />
          {/* Orientation compass — same component as the SCAD viewer.
              Offset up to clear the bottom stat strip below. */}
          <AxesIndicator axes={axes} className="bottom-40 left-12" />
          {viewerError && (
            <div
              data-testid="bd-viewer-error"
              className="absolute inset-x-0 top-0 m-8 rounded-3 border border-red/40 bg-panel px-10 py-6 text-11 text-red"
            >
              Couldn&apos;t load preview: {viewerError}
            </div>
          )}
          {/* Stat strip — mirrors the SCAD viewer's 36px footer. */}
          <div className="absolute inset-x-0 bottom-0 flex items-center gap-12 border-t border-line bg-panel/90 px-12 py-6 font-mono text-10 text-text-mute">
            <span data-testid="bd-preset-label">{activePreset.label}</span>
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

        {/* Right rail: presets + download + read-only params */}
        <aside
          data-testid="bd-detail-rail"
          className="min-h-0 border-t border-line bg-panel p-12 min-[1200px]:overflow-y-auto min-[1200px]:border-l min-[1200px]:border-t-0"
        >
          <p className="m-0 text-12 text-text-dim">{model.blurb}</p>

          {/* Presets-only notice */}
          <div
            data-testid="bd-presets-only-notice"
            className="mt-12 rounded-3 border border-line bg-panel2 px-10 py-8 text-11 text-text-dim"
          >
            <span className="font-semibold text-text">Presets only for now.</span>{" "}
            This is a build123d model — interactive preview and live
            parameter editing aren&apos;t available yet. Pick a preset below to
            view it and download the print-ready STL.
          </div>

          {/* Preset picker */}
          <div className="mt-16 font-mono text-10 uppercase tracking-wide text-text-mute">
            Presets
          </div>
          <div className="mt-6 flex flex-col gap-4" role="listbox" aria-label="Presets">
            {model.presets.map((p) => {
              const active = p.id === activePreset.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  data-testid={`bd-preset-${p.id}`}
                  onClick={() => setActivePresetId(p.id)}
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

          {/* Download */}
          <a
            data-testid="bd-download-stl"
            href={assetUrl(model.slug, activePreset.id, "stl")}
            download={`${model.slug}-${activePreset.id}.stl`}
            className={clsx(
              "mt-16 inline-flex w-full items-center justify-center rounded-3",
              "border border-accent-line bg-accent px-8 py-6",
              "font-semibold text-accent-ink no-underline hover:opacity-90",
            )}
          >
            Download STL
          </a>

          {/* Read-only params for the active preset */}
          <div className="mt-18 font-mono text-10 uppercase tracking-wide text-text-mute">
            Parameters
          </div>
          <table className="mt-6 w-full border-collapse text-12">
            <tbody>
              {model.params.map((param) => (
                <tr key={param.name} className="border-b border-line-soft">
                  <td className="py-3 pr-8 text-text-dim">
                    {param.label ?? param.name}
                  </td>
                  <td className="py-3 text-right font-mono text-text">
                    {formatParamValue(param, activePreset.values[param.name])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </aside>
      </div>
    </div>
  );
}

function formatParamValue(
  param: Param,
  value: Preset["values"][string] | undefined,
): string {
  // A preset only pins the params it changes; unpinned ones show their
  // declared default so the table is never blank.
  const v = value ?? param.default;
  const unit = "unit" in param && param.unit ? ` ${param.unit}` : "";
  if (typeof v === "boolean") return v ? "yes" : "no";
  return `${v}${unit}`;
}
