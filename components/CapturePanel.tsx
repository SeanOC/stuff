"use client";

import { useEffect, useRef, useState } from "react";
import type { DETECTION_ERRORS } from "@/lib/capture/errors";
import type { capture, Point } from "@/lib/capture";
import type { Param, ParamValue } from "@/lib/scad-params/parse";

export const DETECTION_ADVICE: Record<(typeof DETECTION_ERRORS)[number], string> = {
  "no perimeter lattice contrast": "Show the whole baseplate on a plain surface that contrasts with the plate.",
  "no board boundary": "Show the whole baseplate on a plain surface that contrasts with the plate.",
  "board boundary is not a visible rectangle": "Show the whole baseplate on a plain surface that contrasts with the plate.",
  "perimeter does not support a 42 mm lattice": "Use a Gridfinity baseplate 2–6 cells per side.",
  "board touches image edge": "Step back so the whole baseplate is inside the frame.",
  "board obstructed by an object crossing its edge": "Remove anything crossing the plate edge.",
  "item too large for the plate or background not modelled": "Use a bigger plate or move the item inside the grid.",
  "item crosses the plate edge": "Move the item fully inside the baseplate.",
  "no item contour": "The item must contrast with the sheet or plate (colour or brightness).",
  "sheet is not flat or the print is scaled": "Lay the sheet flat and print at 100% scale without fitting to the page.",
  "a reference marker is hidden — keep all four corners visible and uncovered": "Keep all four printed markers visible and uncovered.",
  "item crosses the sheet field": "Move the item fully inside the grey field.",
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
  if (result.grid.kind === "sheet") path([[0,0], [width,0], [width,height], [0,height], [0,0]], "#38bdf8");
  else {
    for (let x = 0; x <= width; x += 42) path([[x, 0], [x, height]], "#38bdf8");
    for (let y = 0; y <= height; y += 42) path([[0, y], [width, y]], "#38bdf8");
  }
  path(result.ring, "#fbbf24");
}

type DetectionState =
  | { kind: "idle" | "loading" }
  | { kind: "ready"; footprint: string; sheet: boolean }
  | { kind: "error"; message: string };

export function CapturePanel({ params, values, onChange, onApply, rendering }: {
  params: Param[];
  values: Record<string, ParamValue>;
  onChange: (name: string, value: ParamValue) => void;
  onApply: (footprint: string) => void;
  rendering: boolean;
}) {
  const [state, setState] = useState<DetectionState>({ kind: "idle" });
  const [barMm, setBarMm] = useState("100");
  const validScale = Number.isFinite(Number(barMm)) && Number(barMm) >= 90 && Number(barMm) <= 110;
  useEffect(() => {
    try {
      const stored = localStorage.getItem("capture.sheetScale");
      if (stored !== null && Number.isFinite(Number(stored)) && Number(stored) >= 90 && Number(stored) <= 110) setBarMm(stored);
    } catch { /* Storage may be unavailable; use the 100 mm default. */ }
  }, []);
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
      const result = await capture(file, { barMm: Number(barMm) });
      if (token !== selection.current || !canvas.current) return;
      drawOverlay(canvas.current, photo, result);
      setState({ kind: "ready", footprint: result.footprint, sheet: result.grid.kind === "sheet" });
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
      <p className="mt-6 text-12 text-text-dim">Place one item inside the grey field of the reference sheet, with all four markers visible. Alternatively, show the whole Gridfinity baseplate on a contrasting plain surface. Photos never leave your browser.</p>
      <p className="mt-6 text-12">Print the reference sheet: <a className="underline" href="/capture/capture-sheet-letter-v1.pdf">Letter</a> · <a className="underline" href="/capture/capture-sheet-a4-v1.pdf">A4</a> (100% scale).</p>
      <label className="mt-8 block text-12" htmlFor="capture-sheet-scale">Measure the check bar on your print:</label>
      <input id="capture-sheet-scale" type="number" min={90} max={110} step="any" value={barMm}
        aria-invalid={!validScale} aria-describedby="capture-scale-help"
        className="mt-4 w-84 rounded-3 border border-line bg-panel px-6 text-12"
        onChange={event => {
          const value = event.target.value;
          setBarMm(value);
          // Changing calibration invalidates the prior outline and any pending capture.
          selection.current++; setState({ kind: "idle" });
          if (Number.isFinite(Number(value)) && Number(value) >= 90 && Number(value) <= 110) {
            try { localStorage.setItem("capture.sheetScale", value); } catch { /* Keep the current session value. */ }
          }
        }} /> <span className="text-12">mm</span>
      <p id="capture-scale-help" className="mt-4 text-11 text-text-dim">{validScale ? "Measure once per print; this browser remembers your value." : "Enter a measurement from 90 to 110 mm."}</p>
      <label className="mt-8 block text-12" htmlFor="capture-photo">Take or choose a photo</label>
      <input id="capture-photo" disabled={!validScale} type="file" accept="image/*" capture="environment"
        className="mt-4 block w-full min-w-0 text-12"
        onChange={event => {
          const file = event.target.files?.[0];
          if (file) void selectFile(file);
          event.target.value = ""; // Allow retrying the same photo.
        }} />
      {state.kind === "loading" && <p role="status" className="mt-8 text-12">loading detector…</p>}
      <canvas ref={canvas} hidden={state.kind !== "ready"} aria-label="Photo with detected lattice and item outline"
        className="mt-8 h-auto w-full rounded-3" />
      {state.kind === "ready" && <p className="mt-4 text-11 text-text-dim">Blue: {state.sheet ? "sheet field" : "42 mm lattice"} · Amber: item outline. Check the outline before applying.</p>}
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
      <p className="mt-4 text-11 text-text-mute">Pale-plate synthetic accuracy: 0.79 mm mean / 1.61 mm max. Dark-plate and real-photo accuracy remain unvalidated.</p>
      <button type="button" disabled={state.kind !== "ready" || rendering}
        className="mt-8 rounded-3 border border-accent-line bg-panel-hi px-10 py-6 text-12 disabled:opacity-50"
        onClick={() => { if (state.kind === "ready") onApply(state.footprint); }}>Apply footprint</button>
    </section>
  );
}
