/** Pale threshold / dark structural capture; see build123d/docs/capture-bins-spike.md. */
import { loadOpenCV } from "./opencv";
import { decodeImage } from "./image";
import { detectGrid } from "./grid";
import { rectify } from "./rectify";
import { segment } from "./segment";
import { footprint } from "./footprint";
import { encode } from "./encode";
export { DetectionError, DETECTION_ERRORS } from "./errors";
export { encode, parse, validate } from "./encode";
export type { Point } from "./encode";

export async function capture(input: Blob | ArrayBuffer, options: { barMm?: number } = {}) {
  const [cv, image] = await Promise.all([loadOpenCV(), decodeImage(input)]);
  const grid = detectGrid(cv, image, .5, options.barMm ?? 100);
  const rectified = rectify(cv, image, grid.H, { sizeMm: grid.sizeMm, kind: grid.kind, polarity: grid.polarity });
  const ring = footprint(cv, segment(cv, rectified), rectified.mmPerPx, rectified.originMm,
    grid.kind === "sheet" ? "item crosses the sheet field" : "item crosses the plate edge");
  return { footprint: encode(ring), ring, grid, rectified };
}
