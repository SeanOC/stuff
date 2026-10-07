/** Bare/paper branch of build123d/capture/footprint.py:42-117.
 * PITCH=42 (:12); period std<3, counts 2..6, epsilon 1e-9, score .60/.06 (:49-69).
 * Board threshold 85 (:95), quad .015*arcLength and .15*area (:100-102),
 * edge guard 2 / w-3 / h-3 (:105), rough warp 840 and strips 12:45 (:107-112).
 * ArUco deliberately excluded: build123d/docs/capture-bins-spike.md:102-108.
 */
import { DetectionError } from "./errors";
import type { CV, Mat } from "./opencv";
import type { Point } from "./encode";
import type { RGBImage } from "./image";
export const PITCH = 42;
export interface Grid { H: number[]; confidence: number; sizeMm: Point; kind: "lattice" }

export function periodCount(profile: number[]): [number, number] {
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
  const candidates = scores.filter(s => s[0] >= Math.max(.60, best - .06));
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

export function detectGrid(cv: CV, image: RGBImage): Grid {
  const { width, height, data } = image;
  if (!(data instanceof Uint8Array) || data.length !== width * height * 3)
    throw new Error("expected RGB uint8 image");
  const owned: { delete(): void }[] = [];
  const own = <T extends { delete(): void }>(item: T): T => { owned.push(item); return item; };
  try {
    const rgb = own(cv.matFromArray(height, width, cv.CV_8UC3, data));
    const gray = own(new cv.Mat()), binary = own(new cv.Mat());
    cv.cvtColor(rgb, gray, cv.COLOR_RGB2GRAY);
    cv.threshold(gray, binary, 85, 255, cv.THRESH_BINARY);
    const contours = own(new cv.MatVector()), hierarchy = own(new cv.Mat());
    cv.findContours(binary, contours, hierarchy, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE);
    if (!contours.size()) throw new DetectionError("no board boundary");
    let largest: Mat | undefined, largestArea = -1;
    for (let i = 0; i < contours.size(); i++) {
      const c = own(contours.get(i)), a = cv.contourArea(c);
      if (a > largestArea) { largest = c; largestArea = a; }
    }
    const quad = own(new cv.Mat());
    cv.approxPolyDP(largest!, quad, .015 * cv.arcLength(largest!, true), true);
    if (quad.rows !== 4 || cv.contourArea(quad) < .15 * width * height)
      throw new DetectionError("board boundary is not a visible rectangle");
    const points = orderedQuad(quad.data32S);
    if (points.some(([x, y]) => x < 2 || y < 2 || x > width - 3 || y > height - 3))
      throw new DetectionError("board touches image edge");
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
    const [nx, cx] = periodCount(px), [ny, cy] = periodCount(py);
    const dst = own(cv.matFromArray(4, 1, cv.CV_32FC2, [0, 0, nx * PITCH, 0, nx * PITCH, ny * PITCH, 0, ny * PITCH]));
    const H = own(cv.getPerspectiveTransform(src, dst));
    return { H: Array.from(H.data64F), confidence: Math.min(cx, cy), sizeMm: [nx * PITCH, ny * PITCH], kind: "lattice" };
  } finally { owned.reverse().forEach(m => m.delete()); }
}
