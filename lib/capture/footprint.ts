/** build123d/capture/footprint.py:217-227: largest RETR_EXTERNAL contour,
 * CHAIN_APPROX_SIMPLE, RDP .3 mm, 3..256 vertices, explicit closing point.
 */
import type { CV, Mat } from "./opencv";
import type { Point } from "./encode";
import type { Mask } from "./segment";
import { MM_PER_PX } from "./rectify";
import { DetectionError } from "./errors";
export function footprint(cv: CV, mask: Mask, mmPerPx = MM_PER_PX, originMm: Point = [0, 0]): Point[] {
  const src = cv.matFromArray(mask.height, mask.width, cv.CV_8UC1, mask.data);
  const contours = new cv.MatVector(), hierarchy = new cv.Mat(), poly = new cv.Mat();
  const handles: Mat[] = [];
  try {
    cv.findContours(src, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
    if (!contours.size()) throw new DetectionError("no item contour");
    let largest: Mat | undefined, largestArea = -1;
    for (let i = 0; i < contours.size(); i++) {
      const c = contours.get(i); handles.push(c);
      const area = cv.contourArea(c);
      if (area > largestArea) { largest = c; largestArea = area; }
    }
    cv.approxPolyDP(largest!, poly, .3 / mmPerPx, true);
    if (poly.rows < 3 || poly.rows > 256)
      throw new DetectionError("contour cannot meet the 0.3 mm / 256 vertex contract");
    const points = Array.from({ length: poly.rows }, (_, i) =>
      [poly.data32S[2 * i] * mmPerPx + originMm[0], poly.data32S[2 * i + 1] * mmPerPx + originMm[1]] as Point);
    return [...points, [...points[0]]];
  } finally { [...handles, src, contours, hierarchy, poly].forEach(m => m.delete()); }
}
