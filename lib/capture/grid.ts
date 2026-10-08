/** Polarity-agnostic lattice detection; Python reference: capture/footprint.py. */
import { DetectionError } from "./errors";
import type { CV } from "./opencv";
import type { Point } from "./encode";
import type { RGBImage } from "./image";
export const PITCH = 42;
export interface Grid { H: number[]; confidence: number; sizeMm: Point; kind: "lattice"; polarity: "pale" | "dark" }

export function periodCount(profile: number[], interior = false): [number, number] {
  const mean = profile.reduce((a, b) => a + b, 0) / profile.length;
  const p = profile.map(v => v - mean);
  if (Math.sqrt(p.reduce((s, v) => s + v * v, 0) / p.length) < 3)
    throw new DetectionError("no perimeter lattice contrast");
  const scores: [number, number][] = [];
  for (let n = 2; n <= 6; n++) {
    const rawLag = p.length / n, lower = Math.floor(rawLag);
    const lag = rawLag - lower === .5 ? lower + lower % 2 : Math.round(rawLag);
    let dot = 0, aa = 0, bb = 0;
    for (let i = 0; i < p.length - lag; i++) {
      dot += p[i] * p[i + lag]; aa += p[i] ** 2; bb += p[i + lag] ** 2;
    }
    scores.push([dot / (Math.sqrt(aa) * Math.sqrt(bb) + 1e-9), n]);
  }
  const best = Math.max(...scores.map(s => s[0]));
  const candidates = scores.filter(s => s[0] >= Math.max(interior ? -Infinity : .60, best - .06));
  if (!candidates.length) throw new DetectionError("perimeter does not support a 42 mm lattice");
  const [score, count] = candidates[candidates.length - 1];
  return [count, score];
}

function orderedQuad(data: Int32Array): Point[] {
  const p = Array.from({ length: 4 }, (_, i) => [data[i * 2], data[i * 2 + 1]] as Point);
  const center = [p.reduce((s, xy) => s + xy[0], 0) / 4, p.reduce((s, xy) => s + xy[1], 0) / 4];
  p.sort((a, b) => Math.atan2(a[1] - center[1], a[0] - center[0]) - Math.atan2(b[1] - center[1], b[0] - center[0]));
  let start = 0;
  for (let i = 1; i < 4; i++) if (p[i][0] + p[i][1] < p[start][0] + p[start][1]) start = i;
  return [...p.slice(start), ...p.slice(0, start)];
}

export function detectGrid(cv: CV, image: RGBImage, confidenceFloor = .5): Grid {
  const { width, height, data } = image;
  if (!(data instanceof Uint8Array) || data.length !== width * height * 3)
    throw new Error("expected RGB uint8 image");
  if (!(confidenceFloor >= .3 && confidenceFloor <= .8)) throw new Error("confidence_floor must be in 0.3..0.8");
  const owned: { delete(): void }[] = [];
  const own = <T extends { delete(): void }>(item: T): T => { owned.push(item); return item; };
  const candidates: Grid[] = [], errors: DetectionError[] = [];
  let obstructed = false;
  try {
    const rgb = own(cv.matFromArray(height, width, cv.CV_8UC3, data));
    const gray = own(new cv.Mat());
    cv.cvtColor(rgb, gray, cv.COLOR_RGB2GRAY);
    for (const polarity of ["pale", "dark"] as const) {
      const binary = own(new cv.Mat());
      cv.threshold(gray, binary, 85, 255, polarity === "pale" ? cv.THRESH_BINARY : cv.THRESH_BINARY_INV);
      const contours = own(new cv.MatVector()), hierarchy = own(new cv.Mat());
      cv.findContours(binary, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
      for (let index = 0; index < contours.size(); index++) {
        const contour = own(contours.get(index));
        if (cv.contourArea(contour) < .15 * width * height) continue;
        const hull = own(new cv.Mat()), hullQuad = own(new cv.Mat());
        cv.convexHull(contour, hull);
        cv.approxPolyDP(hull, hullQuad, .015 * cv.arcLength(hull, true), true);
        if (hullQuad.rows > 4) { obstructed = true; continue; }
        let quad = own(new cv.Mat());
        cv.approxPolyDP(contour, quad, .015 * cv.arcLength(contour, true), true);
        if (quad.rows !== 4 && polarity === "dark") quad = hullQuad;
        if (quad.rows !== 4 || cv.contourArea(quad) < .15 * width * height) {
          errors.push(new DetectionError("board boundary is not a visible rectangle")); continue;
        }
        const points = orderedQuad(quad.data32S);
        if (points.some(([x, y]) => x < 2 || y < 2 || x > width - 3 || y > height - 3)) {
          errors.push(new DetectionError("board touches image edge")); continue;
        }
        const src = own(cv.matFromArray(4, 1, cv.CV_32FC2, points.flat()));
        const square = own(cv.matFromArray(4, 1, cv.CV_32FC2, [0, 0, 839, 0, 839, 839, 0, 839]));
        const roughH = own(cv.getPerspectiveTransform(src, square)), rough = own(new cv.Mat());
        cv.warpPerspective(gray, rough, roughH, new cv.Size(840, 840));
        const px = new Array<number>(840).fill(0), py = new Array<number>(840).fill(0);
        for (let i = 0; i < 840; i++) {
          for (let s = 12; s < 45; s++) {
            px[i] += rough.data[s * 840 + i] + rough.data[(840 - 45 + s - 12) * 840 + i];
            py[i] += rough.data[i * 840 + s] + rough.data[i * 840 + 840 - 45 + s - 12];
          }
          px[i] /= 66; py[i] /= 66;
        }
        let nx: number, ny: number, cx: number, cy: number;
        try {
          try { [nx, cx] = periodCount(px); [ny, cy] = periodCount(py); }
          catch (error) {
            if (!(error instanceof DetectionError)) throw error;
            px.fill(0); py.fill(0);
            for (let y = 0; y < 840; y++) for (let x = 0; x < 840; x++) {
              px[x] += rough.data[y * 840 + x] / 840; py[y] += rough.data[y * 840 + x] / 840;
            }
            [nx, cx] = periodCount(px, true); [ny, cy] = periodCount(py, true);
          }
        } catch (error) {
          if (!(error instanceof DetectionError)) throw error;
          errors.push(error); continue;
        }
        const confidence = Math.min(cx, cy);
        if (confidence < confidenceFloor) {
          errors.push(new DetectionError("perimeter does not support a 42 mm lattice")); continue;
        }
        const dst = own(cv.matFromArray(4, 1, cv.CV_32FC2, [0, 0, nx * PITCH, 0, nx * PITCH, ny * PITCH, 0, ny * PITCH]));
        const H = own(cv.getPerspectiveTransform(src, dst));
        candidates.push({ H: Array.from(H.data64F), confidence, sizeMm: [nx * PITCH, ny * PITCH], kind: "lattice", polarity });
      }
    }
    if (obstructed) throw new DetectionError("board obstructed by an object crossing its edge");
    if (!candidates.length) throw errors[0] ?? new DetectionError("board boundary is not a visible rectangle");
    return candidates.reduce((best, candidate) => candidate.confidence > best.confidence ? candidate : best);
  } finally { owned.reverse().forEach(m => m.delete()); }
}
