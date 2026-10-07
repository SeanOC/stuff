"use client";

import { useEffect, useRef, useState } from "react";
import type { DETECTION_ERRORS } from "@/lib/capture/errors";
import type { capture, Point } from "@/lib/capture";
import type { Param, ParamValue } from "@/lib/scad-params/parse";

export const DETECTION_ADVICE: Record<(typeof DETECTION_ERRORS)[number], string> = {
  "no perimeter lattice contrast": "Show the whole baseplate on a dark, plain surface.",
  "no board boundary": "Show the whole baseplate on a dark, plain surface.",
  "board boundary is not a visible rectangle": "Show the whole baseplate on a dark, plain surface.",
  "perimeter does not support a 42 mm lattice": "Use a Gridfinity baseplate 2–6 cells per side.",
  "board touches image edge": "Step back so the whole baseplate is inside the frame.",
  "no item contour": "The item must contrast with the plate (colour or darker).",
  "contour cannot meet the 0.3 mm / 256 vertex contract": "Simplify the item's outline or move the camera closer.",
};

function adviceFor(message: string): string | undefined {
  if (message === "footprint must fit 6x6 cells (252x252 mm)")
    return "The item is too large for a 6×6 bin.";
  return Object.hasOwn(DETECTION_ADVICE, message)
    ? DETECTION_ADVICE[message as keyof typeof DETECTION_ADVICE]
    : undefined;
}

type CaptureResult = Awaited<ReturnType<typeof capture>>;

// H maps source pixels to board millimetres. Its adjugate maps back;
// the common determinant cancels in the homogeneous division.
export function photoPoint(H: number[], [x, y]: Point): Point {
  const [a, b, c, d, e, f, g, h, i] = H;
  const w = (d * h - e * g) * x + (b * g - a * h) * y + a * e - b * d;
  return [
    ((e * i - f * h) * x + (c * h - b * i) * y + b * f - c * e) / w,
    ((f * g - d * i) * x + (a * i - c * g) * y + c * d - a * f) / w,
  ];
}

function drawOverlay(canvas: HTMLCanvasElement, photo: ImageBitmap, result: CaptureResult) {
  canvas.width = photo.width;
  canvas.height = photo.height;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Could not create image canvas");
  ctx.drawImage(photo, 0, 0);
  ctx.lineWidth = Math.max(2, photo.width / 300);
  const path = (points: Point[], colour: string) => {
    ctx.strokeStyle = colour;
    ctx.beginPath();
    points.forEach((point, index) => {
      const [x, y] = photoPoint(result.grid.H, point);
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
  };
  const [width, height] = result.grid.sizeMm;
  for (let x = 0; x <= width; x += 42) path([[x, 0], [x, height]], "#38bdf8");
  for (let y = 0; y <= height; y += 42) path([[0, y], [width, y]], "#38bdf8");
  path(result.ring, "#fbbf24");
}

type DetectionState =
  | { kind: "idle" | "loading" }
  | { kind: "ready"; footprint: string }
  | { kind: "error"; message: string };

export function CapturePanel({ params, values, onChange, onApply, rendering }: {
  params: Param[];
  values: Record<string, ParamValue>;
  onChange: (name: string, value: ParamValue) => void;
  onApply: (footprint: string) => void;
  rendering: boolean;
}) {
  const [state, setState] = useState<DetectionState>({ kind: "idle" });
  const canvas = useRef<HTMLCanvasElement>(null);
  const selection = useRef(0);
  useEffect(() => () => { selection.current++; }, []);
  const clearance = params.find(p => p.name === "clearance");

  async function selectFile(file: File) {
    const token = ++selection.current;
    setState({ kind: "loading" });
    let photo: ImageBitmap | undefined;
    try {
      // No pipeline code or OpenCV runtime is requested on page view.
      const { capture } = await import("@/lib/capture");
      if (token !== selection.current) return;
      photo = await createImageBitmap(file, { imageOrientation: "from-image" });
      const result = await capture(file);
      if (token !== selection.current || !canvas.current) return;
      drawOverlay(canvas.current, photo, result);
      setState({ kind: "ready", footprint: result.footprint });
    } catch (error) {
      if (token === selection.current)
        setState({ kind: "error", message: error instanceof Error ? error.message : String(error) });
    } finally {
      photo?.close();
    }
  }

  return (
    <section aria-labelledby="capture-heading" className="mt-18 rounded-3 border border-line bg-panel2 p-12">
      <h2 id="capture-heading" className="m-0 text-14 font-semibold">Capture an item outline</h2>
      <p className="mt-6 text-12 text-text-dim">Photos never leave your browser. Show the whole baseplate on a dark, plain surface, with one contrasting item.</p>
      <label className="mt-8 block text-12" htmlFor="capture-photo">Take or choose a photo</label>
      <input id="capture-photo" type="file" accept="image/*" capture="environment"
        className="mt-4 block w-full min-w-0 text-12"
        onChange={event => {
          const file = event.target.files?.[0];
          if (file) void selectFile(file);
          event.target.value = ""; // Allow retrying the same photo.
        }} />
      {state.kind === "loading" && <p role="status" className="mt-8 text-12">loading detector…</p>}
      <canvas ref={canvas} hidden={state.kind !== "ready"} aria-label="Photo with detected lattice and item outline"
        className="mt-8 h-auto w-full rounded-3" />
      {state.kind === "ready" && <p className="mt-4 text-11 text-text-dim">Blue: 42 mm lattice · Amber: item outline. Check the outline before applying.</p>}
      {state.kind === "error" && <div role="alert" className="mt-8 text-12">
        <p>{state.message}</p>
        {adviceFor(state.message) && <p>{adviceFor(state.message)}</p>}
      </div>}
      {clearance?.kind === "number" && <div className="mt-8">
        <label htmlFor="capture-clearance" className="text-12">Pocket clearance: {String(values.clearance)} mm</label>
        <input id="capture-clearance" type="range" className="block w-full"
          min={clearance.min} max={clearance.max} step={clearance.step}
          value={Number(values.clearance)} onChange={event => onChange("clearance", Number(event.target.value))} />
      </div>}
      <p className="mt-8 text-12 text-text-dim">Type pocket depth below yourself. The photo gives the outline only.</p>
      <p className="mt-4 text-11 text-text-mute">Accuracy measured on synthetic renders: 0.79 mm mean / 1.61 mm max. Real-photo measurements are pending.</p>
      <button type="button" disabled={state.kind !== "ready" || rendering}
        className="mt-8 rounded-3 border border-accent-line bg-panel-hi px-10 py-6 text-12 disabled:opacity-50"
        onClick={() => { if (state.kind === "ready") onApply(state.footprint); }}>Apply footprint</button>
    </section>
  );
}
