import type { CV } from "./opencv";
import type { Rectified } from "./rectify";
import { DetectionError } from "./errors";
import { structural, type StructuralOptions } from "./structural";
export interface Mask { width: number; height: number; data: Uint8Array; roi?: Uint8Array }
export function segment(cv: CV, rectified: Rectified, options: StructuralOptions & { method?: "threshold" | "structural" } = {}): Mask {
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
    if (rectified.kind !== "sheet" && rectified.kind !== "aruco" && rectified.polarity === "pale" && whiteCount) {
      const b = cv.boundingRect(white);
      if (whiteCount > .12 * height * width && b.width < .9 * width && b.height < .9 * height) {
        left = b.x + 2; top = b.y + 2; right = b.x + b.width - 2; bottom = b.y + b.height - 2;
      }
    }
    const roi = new Uint8Array(width * height);
    for (let y = top; y < bottom; y++) roi.fill(1, y * width + left, y * width + right);
    if (rectified.kind === "aruco") {
      const corner = Math.round(14 / rectified.mmPerPx);
      for (let y = 0; y < height; y++) for (let x = 0; x < width; x++)
        if ((y < corner || y >= height - corner) && (x < corner || x >= width - corner)) roi[y * width + x] = 0;
    }
    if (rectified.kind === "sheet") {
      if (options.method) throw new Error("sheet segmentation requires the periodic method");
      // A histogram gives NumPy's even-count median exactly without sorting
      // millions of pixels. The gain and clipping are monotone, so the WB
      // median can be read from the same two central histogram values.
      const hist = Array.from({ length: 3 }, () => new Uint32Array(256));
      let count = 0;
      for (let i = 0; i < roi.length; i++) if (roi[i]) {
        count++;
        for (let c = 0; c < 3; c++) hist[c][data[i * 3 + c]]++;
      }
      const middle = hist.map(channel => {
        let total = 0, lo = -1, hi = 0;
        for (let v = 0; v < 256; v++) {
          total += channel[v];
          if (lo < 0 && total > Math.floor((count - 1) / 2)) lo = v;
          if (total > Math.floor(count / 2)) { hi = v; break; }
        }
        return [lo, hi];
      });
      const medians = middle.map(([lo, hi]) => (lo + hi) / 2);
      const mean = medians.reduce((a, b) => a + b, 0) / 3;
      const gains = medians.map(m => mean / Math.max(m, 1));
      const bg = middle.map(([lo, hi], c) => (Math.min(255, lo * gains[c]) + Math.min(255, hi * gains[c])) / 2);
      const bgMean = bg.reduce((a, b) => a + b, 0) / 3;
      for (let i = 0; i < roi.length; i++) {
        const r = Math.min(255, data[i*3] * gains[0]), g = Math.min(255, data[i*3+1] * gains[1]), b = Math.min(255, data[i*3+2] * gains[2]);
        const lightness = (r + g + b) / 3;
        mask.data[i] = Number(roi[i] && (Math.max(r,g,b)-Math.min(r,g,b) > 20 || lightness < .55*bgMean || lightness > 1.30*bgMean));
      }
      const rawSize = 1 / rectified.mmPerPx, floor = Math.floor(rawSize);
      const size = Math.max(1, rawSize - floor === .5 ? floor + floor % 2 : Math.round(rawSize)) | 1;
      const ellipse = cv.getStructuringElement(cv.MORPH_ELLIPSE, new cv.Size(size, size));
      try {
        cv.morphologyEx(mask, closed, cv.MORPH_OPEN, ellipse);
        cv.morphologyEx(closed, mask, cv.MORPH_CLOSE, ellipse);
        return { width, height, data: mask.data.slice(), roi };
      } finally { ellipse.delete(); }
    }
    const method = options.method ?? (rectified.polarity === "dark" ? "structural" : "threshold");
    if (method === "structural") mask.data.set(structural(rectified, roi, options));
    else for (let i = 0; i < width * height; i++) {
      const r = data[3 * i], g = data[3 * i + 1], b = data[3 * i + 2];
      mask.data[i] = Number(roi[i] && (Math.max(r, g, b) - Math.min(r, g, b) > 35 || gray.data[i] < 65));
    }
    cv.morphologyEx(mask, closed, cv.MORPH_CLOSE, kernel);
    if (method === "structural") {
      const count = closed.data.reduce((a, b) => a + b, 0), size = roi.reduce((a, b) => a + b, 0);
      if (count > (options.coverageLimit ?? .35) * size)
        throw new DetectionError("item too large for the plate or background not modelled");
    }
    return { width, height, data: closed.data.slice(), ...(rectified.polarity === "dark" ? { roi } : {}) };
  } finally { [rgb, gray, white, mask, kernel, closed].forEach(m => m.delete()); }
}
