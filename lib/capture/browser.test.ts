// @vitest-environment jsdom
import { afterEach, expect, test, vi } from "vitest";
import { decodeImage } from "./image";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.resetModules(); document.head.innerHTML = ""; });

test("browser decoder requests EXIF orientation, strips alpha, and closes the bitmap", async () => {
  const bitmap = { width: 2, height: 1, close: vi.fn() };
  const create = vi.fn().mockResolvedValue(bitmap);
  vi.stubGlobal("createImageBitmap", create);
  const draw = vi.fn();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    drawImage: draw,
    getImageData: () => ({ data: new Uint8ClampedArray([255, 12, 3, 255, 4, 5, 200, 255]) }),
  } as unknown as ReturnType<HTMLCanvasElement["getContext"]>);
  const blob = new Blob([new Uint8Array([1])]);
  const decoded = await decodeImage(blob);
  expect(create).toHaveBeenCalledWith(blob, { imageOrientation: "from-image" });
  expect(draw).toHaveBeenCalledWith(bitmap, 0, 0);
  expect(decoded).toEqual({ width: 2, height: 1, data: new Uint8Array([255, 12, 3, 4, 5, 200]) });
  expect(bitmap.close).toHaveBeenCalledOnce();
});

test("bitmap is released if canvas allocation fails", async () => {
  const bitmap = { width: 1, height: 1, close: vi.fn() };
  vi.stubGlobal("createImageBitmap", vi.fn().mockResolvedValue(bitmap));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  await expect(decodeImage(new ArrayBuffer(1))).rejects.toThrow("Could not create image canvas");
  expect(bitmap.close).toHaveBeenCalledOnce();
});

test("browser loader inserts one script, waits for runtime, and preserves its initializer", async () => {
  const { loadOpenCV } = await import("./opencv");
  const first = loadOpenCV();
  expect(loadOpenCV()).toBe(first);
  const scripts = document.head.querySelectorAll("script");
  expect(scripts).toHaveLength(1);
  expect(scripts[0].getAttribute("src")).toBe(["", "vendor", "opencv", "opencv.js"].join("/"));
  const initialize = vi.fn();
  const cv = { onRuntimeInitialized: initialize, then: vi.fn(), Mat: undefined as unknown };
  vi.stubGlobal("cv", cv);
  scripts[0].dispatchEvent(new Event("load"));
  let ready = false;
  void first.then(() => { ready = true; });
  await Promise.resolve();
  expect(ready).toBe(false);
  cv.Mat = class {};
  cv.onRuntimeInitialized();
  expect(await first).toBe(cv);
  expect(initialize).toHaveBeenCalledOnce();
  expect(cv.then).toBeUndefined();
  expect(loadOpenCV()).toBe(first);
});

test("browser loader surfaces script network failures", async () => {
  const { loadOpenCV } = await import("./opencv");
  const pending = loadOpenCV();
  document.head.querySelector("script")!.dispatchEvent(new Event("error"));
  await expect(pending).rejects.toThrow("Could not load OpenCV");
});

test("browser loader surfaces WASM initialization failures", async () => {
  const { loadOpenCV } = await import("./opencv");
  const pending = loadOpenCV();
  const cv = { onAbort: undefined as undefined | ((reason: unknown) => void) };
  vi.stubGlobal("cv", cv);
  document.head.querySelector("script")!.dispatchEvent(new Event("load"));
  cv.onAbort!("compile failed");
  await expect(pending).rejects.toThrow("OpenCV initialization failed: compile failed");
});
