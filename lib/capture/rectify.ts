/** build123d/capture/footprint.py:13,120-143: 0.20 mm/px, 4096 limit,
 * ceil(extent/scale - 1e-9); optional full-image extent includes last sample.
 */
import type { Point } from "./encode";
import type { RGBImage } from "./image";
import type { CV } from "./opencv";
export const MM_PER_PX = .2;
export interface Rectified {
  image: RGBImage;
  mmPerPx: number;
  originMm: Point;
  polarity: "pale" | "dark";
  kind: "bare" | "paper" | "lattice";
}
export function rectify(cv: CV, image: RGBImage, H: number[], options: {
  mmPerPx?: number; sizeMm?: Point; kind?: Rectified["kind"]; polarity?: Rectified["polarity"];
} = {}): Rectified {
  const mmPerPx = options.mmPerPx ?? MM_PER_PX;
  if (!Number.isFinite(mmPerPx) || mmPerPx <= 0) throw new Error("mm_per_px must be positive");
  let originMm: Point = [0, 0], sizeMm = options.sizeMm;
  if (!sizeMm) {
    const corners = [[0, 0], [image.width - 1, 0], [image.width - 1, image.height - 1], [0, image.height - 1]];
    const mapped = corners.map(([x, y]) => {
      const w = H[6] * x + H[7] * y + H[8];
      return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w];
    });
    originMm = [0, 1].map(k => Math.floor(Math.min(...mapped.map(p => p[k])) / mmPerPx) * mmPerPx) as Point;
    sizeMm = [0, 1].map(k => Math.max(...mapped.map(p => p[k])) - originMm[k]) as Point;
  }
  const [width, height] = sizeMm.map(s => Math.ceil(s / mmPerPx - 1e-9) + Number(!options.sizeMm));
  if (![width, height].every(s => Number.isFinite(s) && s > 0 && s <= 4096))
    throw new Error("invalid or excessive rectified extent");
  const matrix = [...H];
  for (let j = 0; j < 3; j++) {
    matrix[j] = (H[j] - originMm[0] * H[6 + j]) / mmPerPx;
    matrix[3 + j] = (H[3 + j] - originMm[1] * H[6 + j]) / mmPerPx;
  }
  const src = cv.matFromArray(image.height, image.width, cv.CV_8UC3, image.data);
  const transform = cv.matFromArray(3, 3, cv.CV_64F, matrix), dst = new cv.Mat();
  try {
    cv.warpPerspective(src, dst, transform, new cv.Size(width, height));
    return { image: { width, height, data: dst.data.slice() }, mmPerPx, originMm, kind: options.kind ?? "bare", polarity: options.polarity ?? "pale" };
  } finally { src.delete(); transform.delete(); dst.delete(); }
}
