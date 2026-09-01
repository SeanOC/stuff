"use client";

// Orientation compass — a bottom-left X/Y/Z gizmo shared by both preview
// paths. When the live camera has fired at least one onCameraChange
// (axes != null) the three lines point in the screen-space direction of
// the world X/Y/Z basis vectors. Before that (cold mount, before the
// scene boots) it falls back to a preset-name-driven static orientation
// so the indicator isn't blank. (st-oc3)
//
// Extracted from ViewerChrome (pst-6ram) so the build123d GLB viewer can
// render the very same compass rather than a visual copy. The SCAD path
// keeps its exact DOM/test contract: ViewerChrome renders <AxesIndicator>
// with the same data-testid / data-preset / data-axis attributes.

import clsx from "clsx";
import type { CameraAxes } from "./StlViewer";
import type { CameraPreset } from "@/hooks/useDetailState";

export function AxesIndicator({
  axes,
  preset = "iso",
  className = "bottom-12 left-12",
}: {
  axes: CameraAxes | null;
  /** Drives the aria-label, data-preset attr, and the static fallback. */
  preset?: CameraPreset;
  /** Positioning override — the GLB viewer clears its own stat strip. */
  className?: string;
}) {
  // SVG viewBox is 72×72; keep the origin near the bottom-left quadrant
  // (26, 46) to match the visual placement within the 56×56 frame. Line
  // length R is 22px so the labels sit clear of the origin on all
  // orientations.
  const cx = 26;
  const cy = 46;
  const R = 22;
  return (
    <div
      className={clsx("pointer-events-none absolute font-mono text-10", className)}
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
