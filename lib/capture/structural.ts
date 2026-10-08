/** Python _structural parity: phase median, six background-inlier fits, local
 * RGB envelopes, median+k*MAD. No image-specific colours or class map. */
import { DetectionError } from "./errors";
import type { Rectified } from "./rectify";
export interface StructuralOptions { k?: number; coverageLimit?: number; shiftTolerance?: number }
export function median(values: Float64Array | number[]): number {
  const sorted = values.slice().sort((a, b) => a - b), mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}
export function structural(rect: Rectified, roi: Uint8Array, options: StructuralOptions): Uint8Array {
  const { k = 5, coverageLimit = .35, shiftTolerance = 2 } = options;
  if (!(k >= 3 && k <= 8 && coverageLimit >= .2 && coverageLimit <= .5))
    throw new Error("k must be in 3..8 and coverage_limit in 0.2..0.5");
  if (![1, 2, 3].includes(shiftTolerance)) throw new Error("shift_tolerance must be 1, 2 or 3 pixels");
  const { width, height, data } = rect.image, raw = 42 / rect.mmPerPx, lower = Math.floor(raw);
  const pitch = raw - lower === .5 ? lower + lower % 2 : Math.round(raw);
  const nx = Math.floor(width / pitch), ny = Math.floor(height / pitch), count = pitch * pitch;
  if (nx * ny < 4) throw new DetectionError("item too large for the plate or background not modelled");
  const template = new Float64Array(count * 3), samples = new Float64Array(nx * ny);
  for (let y = 0; y < pitch; y++) for (let x = 0; x < pitch; x++) for (let c = 0; c < 3; c++) {
    for (let iy = 0; iy < ny; iy++) for (let ix = 0; ix < nx; ix++)
      samples[iy * nx + ix] = data[((iy * pitch + y) * width + ix * pitch + x) * 3 + c];
    template[(y * pitch + x) * 3 + c] = median(samples);
  }
  const levels = new Float64Array(count);
  for (let i = 0; i < count; i++) levels[i] = (template[i*3]+template[i*3+1]+template[i*3+2])/3;
  const sorted = levels.slice().sort((a,b)=>a-b);
  const cuts = [.25,.5,.75].map(q => {
    const index = (count-1)*q, lo = Math.floor(index), f = index-lo;
    return sorted[lo]*(1-f)+sorted[Math.ceil(index)]*f;
  });
  const groups: number[][] = [[],[],[],[]];
  for (let i = 0; i < count; i++) groups[cuts.filter(cut=>levels[i]>=cut).length].push(i);
  const residual = new Float64Array(width * height).fill(Infinity);
  for (let iy = 0; iy < ny; iy++) for (let ix = 0; ix < nx; ix++) {
    const tile = new Float64Array(count * 3), error = new Float64Array(count), good = new Uint8Array(count);
    for (let y = 0; y < pitch; y++) for (let x = 0; x < pitch; x++) for (let c = 0; c < 3; c++)
      tile[(y * pitch + x) * 3 + c] = data[((iy * pitch + y) * width + ix * pitch + x) * 3 + c];
    let gain = [1, 1, 1], offset = [0, 0, 0];
    const selectInliers = () => {
      for (let i = 0; i < count; i++) {
        let sum = 0;
        for (let c = 0; c < 3; c++) sum += (tile[i * 3 + c] - template[i * 3 + c] * gain[c] - offset[c]) ** 2;
        error[i] = Math.sqrt(sum);
      }
      // Trim within learned intensity strata so both light and dark
      // background pixels constrain the gain/offset regression.
      for (const group of groups) {
        if (!group.length) continue;
        const values = group.map(i=>error[i]), mid = median(values);
        const threshold = Math.max(1,mid+2*median(values.map(v=>Math.abs(v-mid))));
        for (const i of group) good[i] = Number(error[i] <= threshold);
      }
    };
    selectInliers();
    for (let iteration = 0; iteration < 6; iteration++) {
      const xm = [0, 0, 0], ym = [0, 0, 0]; let n = 0;
      for (let i = 0; i < count; i++) if (good[i]) {
        n++;
        for (let c = 0; c < 3; c++) { xm[c] += template[i * 3 + c]; ym[c] += tile[i * 3 + c]; }
      }
      for (let c = 0; c < 3; c++) { xm[c] /= n; ym[c] /= n; }
      const variance = [0, 0, 0], covariance = [0, 0, 0];
      for (let i = 0; i < count; i++) if (good[i]) for (let c = 0; c < 3; c++) {
        const dx = template[i * 3 + c] - xm[c];
        variance[c] += dx * dx; covariance[c] += dx * (tile[i * 3 + c] - ym[c]);
      }
      gain = variance.map((v, c) => v > 1 ? covariance[c] / v : 1);
      offset = ym.map((v, c) => v - gain[c] * xm[c]);
      selectInliers();
    }
    for (let y = 0; y < pitch; y++) for (let x = 0; x < pitch; x++) {
      let sum = 0;
      for (let c = 0; c < 3; c++) {
        let lo = Infinity, hi = -Infinity;
        for (let dy = -shiftTolerance; dy <= shiftTolerance; dy++) for (let dx = -shiftTolerance; dx <= shiftTolerance; dx++) {
          const j = (((y + dy + pitch) % pitch) * pitch + (x + dx + pitch) % pitch) * 3 + c;
          const bg = template[j] * gain[c] + offset[c];
          lo = Math.min(lo, bg); hi = Math.max(hi, bg);
        }
        const value = tile[(y * pitch + x) * 3 + c];
        sum += (value - Math.max(lo, Math.min(hi, value))) ** 2;
      }
      residual[(iy * pitch + y) * width + ix * pitch + x] = Math.sqrt(sum);
    }
  }
  const values = residual.filter((_, i) => roi[i] !== 0), mid = median(values);
  const threshold = Math.max(1, mid + k * median(values.map(v => Math.abs(v - mid))));
  return Uint8Array.from(residual, (v, i) => Number(roi[i] !== 0 && v > threshold));
}
