/** RGB uint8, matching build123d/capture/footprint.py:79-81 (never BGR).
 * Browser decoding honours EXIF; node fixture decoding uses the dev-only pngjs.
 */
export interface RGBImage { width: number; height: number; data: Uint8Array }

function fromRGBA(width: number, height: number, rgba: Uint8Array | Uint8ClampedArray): RGBImage {
  const data = new Uint8Array(width * height * 3);
  for (let i = 0; i < width * height; i++) data.set(rgba.subarray(i * 4, i * 4 + 3), i * 3);
  return { width, height, data };
}

export async function decodeImage(input: Blob | ArrayBuffer): Promise<RGBImage> {
  if (typeof window === "undefined") {
    const moduleName = "node:module";
    const { createRequire } = await import(/* webpackIgnore: true */ moduleName);
    const require = createRequire(`${process.cwd()}/package.json`);
    const { PNG } = require("pngjs");
    const bytes = input instanceof ArrayBuffer ? input : await input.arrayBuffer();
    const png = PNG.sync.read(Buffer.from(bytes));
    return fromRGBA(png.width, png.height, png.data);
  }
  const blob = input instanceof Blob ? input : new Blob([input]);
  const bitmap = await createImageBitmap(blob, { imageOrientation: "from-image" });
  try {
    const canvas = document.createElement("canvas");
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) throw new Error("Could not create image canvas");
    context.drawImage(bitmap, 0, 0);
    return fromRGBA(bitmap.width, bitmap.height, context.getImageData(0, 0, bitmap.width, bitmap.height).data);
  } finally {
    bitmap.close();
  }
}
