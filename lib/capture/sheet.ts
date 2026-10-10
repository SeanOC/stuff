/** Marker calibration: capture/footprint.py detect_grid and _partial_sheet. */
import profiles from "../../public/capture/sheets.json";
import type { CV } from "./opencv";
import type { Point } from "./encode";
import type { Grid } from "./grid";
import type { MarkerCorners } from "./markers";
import { DetectionError } from "./errors";
export const SHEET_PROFILES = profiles;

function corners(sheet: (typeof profiles)["letter-v1"], ids: number[]): Point[] {
  const size = sheet.marker_size_mm;
  return ids.flatMap(id => {
    const [x, y] = sheet.markers_mm[String(id) as keyof typeof sheet.markers_mm];
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size]] as Point[];
  });
}

function fit(cv: CV, source: Point[], target: Point[], tolerance: number) {
  const src = cv.matFromArray(source.length, 1, cv.CV_32FC2, source.flat());
  const dst = cv.matFromArray(target.length, 1, cv.CV_32FC2, target.flat());
  const inliers = new cv.Mat(), projected = new cv.Mat();
  const H = cv.findHomography(src, dst, tolerance ? cv.RANSAC : 0, tolerance, inliers);
  try {
    if (!H.rows) return;
    cv.perspectiveTransform(src, projected, H);
    const points = source.map((_, i) => [projected.data32F[i * 2], projected.data32F[i * 2 + 1]] as Point);
    const errors = points.map((p, i) => Math.hypot(p[0] - dst.data32F[i * 2], p[1] - dst.data32F[i * 2 + 1]));
    return { H: Array.from(H.data64F), points, errors,
      error: errors.reduce((a, b) => a + b, 0) / source.length,
      inliers: inliers.data.reduce((a, b) => a + b, 0) };
  } finally { src.delete(); dst.delete(); inliers.delete(); projected.delete(); H.delete(); }
}

export function markerGrid(cv: CV, found: Map<number, MarkerCorners>, barMm: number): Grid | undefined {
  const ids = [...found.keys()].sort(), src = ids.flatMap(id => found.get(id)!);
  if (ids.length === 4) {
    const legacy = fit(cv, src, [[3,3],[13,3],[13,13],[3,13], [71,3],[81,3],[81,13],[71,13],
      [71,71],[81,71],[81,81],[71,81], [3,71],[13,71],[13,81],[3,81]], .4);
    if (legacy && legacy.inliers >= 14)
      return { H: legacy.H, kind: "aruco", confidence: Math.exp(-legacy.error), sizeMm: [84,84] };
    const fits = Object.entries(profiles).flatMap(([sheetId, profile]) => {
      const result = fit(cv, src, corners(profile, ids), .8);
      return result ? [{ ...result, sheetId, profile }] : [];
    }).sort((a, b) => a.error - b.error);
    const best = fits[0];
    if (!best || best.error >= .8) throw new DetectionError("sheet is not flat or the print is scaled");
    const [x0,y0,x1,y1] = best.profile.field_mm, k = barMm / 100, H = [...best.H];
    for (let j = 0; j < 3; j++) {
      H[j] = k * (best.H[j] - x0 * best.H[j + 6]);
      H[j + 3] = k * (best.H[j + 3] - y0 * best.H[j + 6]);
    }
    return { H, confidence: Math.exp(-best.error), sizeMm: [(x1-x0)*k, (y1-y0)*k],
      kind: "sheet", sheetId: best.sheetId, reprojectionMm: best.error };
  }
  if (ids.length === 2 || ids.length === 3) {
    for (const sheet of Object.values(profiles)) {
      const target = corners(sheet, ids), result = fit(cv, src, target, 0), size = sheet.marker_size_mm;
      if (!result || result.errors.some(e => e > .1 * size)) continue;
      const p = result.points;
      if (p.some((a, i) => {
        const b = p[Math.floor(i / 4) * 4 + (i + 1) % 4];
        return Math.abs(Math.hypot(a[0]-b[0], a[1]-b[1]) - size) > .1 * size;
      })) continue;
      const centers = (points: Point[]) => ids.map((_, i) => [0, 1].map(axis =>
        points.slice(i*4, i*4+4).reduce((sum, xy) => sum + xy[axis], 0) / 4) as Point);
      const actual = centers(p), expected = centers(target);
      if (actual.every((a, i) => actual.slice(0, i).every((b, j) => Math.abs(
        Math.hypot(a[0]-b[0], a[1]-b[1]) / Math.hypot(expected[i][0]-expected[j][0], expected[i][1]-expected[j][1]) - 1) <= .1)))
        throw new DetectionError("a reference marker is hidden — keep all four corners visible and uncovered");
    }
  }
}
