/** Lazy runtime boundary. The official release includes WASM in its JS file.
 * No OpenCV code is imported or evaluated until loadOpenCV() is called.
 */
export interface Mat {
  rows: number;
  cols: number;
  data: Uint8Array;
  data32S: Int32Array;
  data32F: Float32Array;
  data64F: Float64Array;
  delete(): void;
}
interface MatVector { size(): number; get(index: number): Mat; delete(): void }
export interface CV {
  Mat: { new(rows?: number, cols?: number, type?: number): Mat; ones(rows: number, cols: number, type: number): Mat };
  MatVector: new() => MatVector;
  Size: new(width: number, height: number) => { width: number; height: number };
  CV_8UC1: number; CV_8UC3: number; CV_32FC2: number; CV_64F: number;
  COLOR_RGB2GRAY: number; THRESH_BINARY: number; THRESH_BINARY_INV: number; RETR_EXTERNAL: number;
  CHAIN_APPROX_SIMPLE: number; MORPH_CLOSE: number; MORPH_OPEN: number; MORPH_ELLIPSE: number;
  RETR_LIST: number; ADAPTIVE_THRESH_MEAN_C: number; THRESH_OTSU: number; RANSAC: number;
  matFromArray(rows: number, cols: number, type: number, data: number[] | Uint8Array): Mat;
  cvtColor(src: Mat, dst: Mat, code: number): void;
  threshold(src: Mat, dst: Mat, threshold: number, max: number, type: number): void;
  adaptiveThreshold(src: Mat, dst: Mat, max: number, method: number, type: number, blockSize: number, c: number): void;
  isContourConvex(src: Mat): boolean;
  findHomography(src: Mat, dst: Mat, method: number, tolerance?: number, mask?: Mat): Mat;
  perspectiveTransform(src: Mat, dst: Mat, transform: Mat): void;
  getStructuringElement(shape: number, size: { width: number; height: number }): Mat;
  findContours(src: Mat, contours: MatVector, hierarchy: Mat, mode: number, method: number): void;
  contourArea(contour: Mat): number;
  convexHull(src: Mat, dst: Mat): void;
  arcLength(contour: Mat, closed: boolean): number;
  approxPolyDP(src: Mat, dst: Mat, epsilon: number, closed: boolean): void;
  getPerspectiveTransform(src: Mat, dst: Mat): Mat;
  warpPerspective(src: Mat, dst: Mat, transform: Mat, size: { width: number; height: number }): void;
  boundingRect(src: Mat): { x: number; y: number; width: number; height: number };
  morphologyEx(src: Mat, dst: Mat, operation: number, kernel: Mat): void;
  getBuildInformation(): string;
  onRuntimeInitialized?: () => void;
  onAbort?: (reason: unknown) => void;
}
let pending: Promise<CV> | undefined;

// Some Emscripten releases expose a self-resolving thenable. Resolve a wrapper
// first so Promise assimilation cannot recurse forever on that object.
function initialized(cv: CV): Promise<{ cv: CV }> {
  return new Promise((resolve, reject) => {
    if (cv.Mat) { resolve({ cv }); return; }
    const previous = cv.onRuntimeInitialized;
    cv.onRuntimeInitialized = () => { previous?.(); resolve({ cv }); };
    cv.onAbort = reason => reject(new Error(`OpenCV initialization failed: ${String(reason)}`));
  });
}

export function loadOpenCV(): Promise<CV> {
  if (pending) return pending;
  pending = (async () => {
    let module: CV;
    if (typeof window === "undefined") {
      // Dynamic and ignored by the browser bundler: this branch is for node tests.
      const moduleName = "node:module";
      const { createRequire } = await import(/* webpackIgnore: true */ moduleName);
      const require = createRequire(`${process.cwd()}/package.json`);
      module = require(`${process.cwd()}/public/vendor/opencv/opencv.js`) as CV;
    } else {
      module = await new Promise<CV>((resolve, reject) => {
        const script = document.createElement("script");
        script.src = "/vendor/opencv/opencv.js";
        script.async = true;
        script.onload = () => {
          const cv = (window as unknown as { cv: CV }).cv;
          // Do not hand a thenable to resolve.
          initialized(cv).then(({ cv: ready }) => {
            Object.defineProperty(ready, "then", { value: undefined, configurable: true });
            resolve(ready);
          }, reject);
        };
        script.onerror = () => reject(new Error("Could not load OpenCV"));
        document.head.appendChild(script);
      });
    }
    const { cv } = await initialized(module);
    Object.defineProperty(cv, "then", { value: undefined, configurable: true });
    return cv;
  })();
  return pending;
}
