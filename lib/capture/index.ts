/** Threshold-only bare/paper capture; see build123d/docs/capture-bins-spike.md:180-190. */
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

export async function capture(input: Blob | ArrayBuffer) {
  const [cv, image] = await Promise.all([loadOpenCV(), decodeImage(input)]);
  const grid = detectGrid(cv, image);
  const rectified = rectify(cv, image, grid.H, { sizeMm: grid.sizeMm, kind: grid.kind });
  const ring = footprint(cv, segment(cv, rectified), rectified.mmPerPx, rectified.originMm);
  return { footprint: encode(ring), ring, grid, rectified };
}
