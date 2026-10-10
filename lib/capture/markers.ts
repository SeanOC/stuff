/** Four DICT_4X4_50 codes, generated from OpenCV bytesList (see capture docs).
 * The runtime is supplied by loadOpenCV's caller; no ArUco module is required.
 */
import type { CV } from "./opencv";
import type { RGBImage } from "./image";
import type { Point } from "./encode";

export const MARKER_CODES = [
  "1011010100110010", "0000111110011010", "0011001100101101", "1001100101000110",
] as const;
export type MarkerCorners = [Point, Point, Point, Point];

export function detectMarkers(cv: CV, image: RGBImage): Map<number, MarkerCorners> {
  const rgb = cv.matFromArray(image.height, image.width, cv.CV_8UC3, image.data);
  const gray = new cv.Mat();
  const found = new Map<number, MarkerCorners>(), areas = new Map<number, number>();
  try {
    cv.cvtColor(rgb, gray, cv.COLOR_RGB2GRAY);
    // Match ArUco's adaptive windows and polygon approximation. Multiple windows
    // recover both small synthetic markers and unevenly lit phone photographs.
    for (const window of [3, 13, 23]) {
      const binary = new cv.Mat(), contours = new cv.MatVector(), hierarchy = new cv.Mat();
      try {
        cv.adaptiveThreshold(gray, binary, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY_INV, window, 7);
        cv.findContours(binary, contours, hierarchy, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE);
        for (let i = 0; i < contours.size(); i++) {
          const contour = contours.get(i), quad = new cv.Mat();
          try {
            const perimeter = cv.arcLength(contour, true);
            if (perimeter < 48) continue;
            cv.approxPolyDP(contour, quad, .03 * perimeter, true);
            if (quad.rows !== 4 || !cv.isContourConvex(quad)) continue;
            const points = Array.from({ length: 4 }, (_, j) => [quad.data32S[j * 2], quad.data32S[j * 2 + 1]] as Point);
            if (points.some((p, j) => Math.hypot(p[0] - points[(j + 1) % 4][0], p[1] - points[(j + 1) % 4][1]) < 12)) continue;
            // Clockwise in image coordinates; the decoder resolves the start.
            const [a, b, c] = points;
            if ((b[0]-a[0])*(c[1]-b[1]) - (b[1]-a[1])*(c[0]-b[0]) < 0) points.reverse();
            const decoded = decodeQuad(cv, gray, points);
            // Rank the quadrilateral, not the noisy contour: an inner border
            // can have a longer jagged perimeter than the outer marker edge.
            const area = cv.contourArea(quad);
            if (!decoded || area <= (areas.get(decoded.id) ?? 0)) continue;
            found.set(decoded.id, Array.from({ length: 4 }, (_, j) => points[(j + decoded.rotation) % 4]) as MarkerCorners);
            areas.set(decoded.id, area);
          } finally { contour.delete(); quad.delete(); }
        }
      } finally { binary.delete(); contours.delete(); hierarchy.delete(); }
    }
    return found;
  } finally { rgb.delete(); gray.delete(); }
}

function decodeQuad(cv: CV, gray: ReturnType<CV["matFromArray"]>, points: Point[]) {
  const src = cv.matFromArray(4, 1, cv.CV_32FC2, points.flat());
  const dst = cv.matFromArray(4, 1, cv.CV_32FC2, [10,10,69,10,69,69,10,69]);
  const H = cv.getPerspectiveTransform(src, dst), patch = new cv.Mat(), binary = new cv.Mat();
  try {
    cv.warpPerspective(gray, patch, H, new cv.Size(80, 80));
    cv.threshold(patch, binary, 0, 255, cv.THRESH_BINARY | cv.THRESH_OTSU);
    const cells: number[][] = [];
    let border = 0, surround = 0;
    for (let y = 0; y < 8; y++) {
      cells[y] = [];
      for (let x = 0; x < 8; x++) {
        let white = 0, intensity = 0;
        for (let dy = 3; dy < 7; dy++) for (let dx = 3; dx < 7; dx++) {
          const offset = (y * 10 + dy) * 80 + x * 10 + dx;
          white += Number(binary.data[offset] > 0); intensity += patch.data[offset] / 16;
        }
        cells[y][x] = Number(white > 8);
        if (x === 0 || y === 0 || x === 7 || y === 7) surround += intensity / 28;
        else if (x === 1 || y === 1 || x === 6 || y === 6) {
          if (white > 8) return;
          border += intensity / 20;
        }
      }
    }
    if (surround < border + 20) return;
    for (let rotation = 0; rotation < 4; rotation++) for (let id = 0; id < 4; id++) {
      let distance = 0;
      for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) {
        let xx = x, yy = y;
        for (let r = 0; r < rotation; r++) [xx, yy] = [3 - yy, xx];
        distance += Number(cells[yy + 2][xx + 2] !== Number(MARKER_CODES[id][y * 4 + x]));
      }
      if (distance <= 1) return { id, rotation };
    }
  } finally { src.delete(); dst.delete(); H.delete(); patch.delete(); binary.delete(); }
}
