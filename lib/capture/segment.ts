/** build123d/capture/footprint.py:146-174,214: inset 3 mm; white min>225,
 * white area>.12*h*w and bounds<.9*w/.9*h with 2px inset; chroma>35 or
 * gray<65; 3x3 MORPH_CLOSE. No ArUco corner exclusion or alternate methods.
 */
import type { CV } from "./opencv";
import type { Rectified } from "./rectify";
export interface Mask { width: number; height: number; data: Uint8Array }
export function segment(cv: CV, rectified: Rectified): Mask {
  const { width, height, data } = rectified.image;
  const rgb = cv.matFromArray(height, width, cv.CV_8UC3, data);
  const gray = new cv.Mat(), white = new cv.Mat(height, width, cv.CV_8UC1);
  const mask = new cv.Mat(height, width, cv.CV_8UC1), kernel = cv.Mat.ones(3, 3, cv.CV_8UC1), closed = new cv.Mat();
  try {
    cv.cvtColor(rgb, gray, cv.COLOR_RGB2GRAY);
    // Python round() uses ties-to-even, including for caller-selected resolution.
    const rawInset = 3 / rectified.mmPerPx, lower = Math.floor(rawInset);
    const inset = rawInset - lower === .5 ? lower + lower % 2 : Math.round(rawInset);
    let left = inset, top = inset, right = width - inset, bottom = height - inset;
    let whiteCount = 0;
    for (let i = 0; i < width * height; i++) {
      const isWhite = Number(Math.min(data[3 * i], data[3 * i + 1], data[3 * i + 2]) > 225);
      white.data[i] = isWhite; whiteCount += isWhite;
    }
    if (whiteCount) {
      const b = cv.boundingRect(white);
      if (whiteCount > .12 * height * width && b.width < .9 * width && b.height < .9 * height) {
        left = b.x + 2; top = b.y + 2; right = b.x + b.width - 2; bottom = b.y + b.height - 2;
      }
    }
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
      const i = y * width + x, r = data[3 * i], g = data[3 * i + 1], b = data[3 * i + 2];
      mask.data[i] = Number(x >= left && x < right && y >= top && y < bottom &&
        (Math.max(r, g, b) - Math.min(r, g, b) > 35 || gray.data[i] < 65));
    }
    cv.morphologyEx(mask, closed, cv.MORPH_CLOSE, kernel);
    return { width, height, data: closed.data.slice() };
  } finally { [rgb, gray, white, mask, kernel, closed].forEach(m => m.delete()); }
}
