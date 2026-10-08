import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, test } from "vitest";
import { capture, DetectionError } from "./index";
import { area, encode, parse, validate, type Point } from "./encode";
import { loadOpenCV } from "./opencv";
import { decodeImage } from "./image";
import { rectify } from "./rectify";
import { detectGrid, periodCount } from "./grid";
import { segment } from "./segment";
import { footprint } from "./footprint";

const fixtures = path.join(process.cwd(), "build123d/tests/fixtures/capture");
const baseline = JSON.parse(readFileSync(path.join(fixtures, "python-footprints.json"), "utf8")) as {
  records: { png: string; result: string; footprint: string | null; error: string | null;
    vertices: number; kind: string | null; truth_mm: Point[] }[];
};
const real = JSON.parse(readFileSync(path.join(fixtures, "real/real-footprints.json"), "utf8")) as {
  records: { png: string; result: string; footprint: string | null; error: string | null;
    kind: string | null; polarity: string | null; method: string }[];
};
const structuralOracle = JSON.parse(readFileSync(path.join(fixtures,"structural-footprints.json"),"utf8")) as
  Record<"plain" | "illuminated", {ring: Point[]; method: string; polarity: string}>;
function bytes(png: string): ArrayBuffer {
  return Uint8Array.from(readFileSync(path.join(fixtures, png))).buffer;
}
function pointToSegment(p: Point, a: Point, b: Point): number {
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy || 1)));
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}
// Sample the entire boundary at <=.02 mm, not just RDP vertices. Adding half
// the maximum sample spacing is a conservative upper bound (distance is 1-Lipschitz).
function directed(a: Point[], b: Point[]): number {
  let worst = 0;
  for (let i = 0; i < a.length - 1; i++) {
    const p = a[i], q = a[i + 1];
    const steps = Math.max(1, Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / .02));
    for (let s = 0; s <= steps; s++) {
      const point: Point = [p[0] + (q[0] - p[0]) * s / steps, p[1] + (q[1] - p[1]) * s / steps];
      let nearest = Infinity;
      for (let j = 0; j < b.length - 1; j++) nearest = Math.min(nearest, pointToSegment(point, b[j], b[j + 1]));
      worst = Math.max(worst, nearest);
    }
  }
  return worst;
}
function hausdorff(a: Point[], b: Point[]): number {
  if (JSON.stringify(a) === JSON.stringify(b)) return 0;
  return Math.max(directed(a, b), directed(b, a)) + .01;
}
function closed(ring: Point[]): Point[] {
  return ring[0][0] === ring.at(-1)![0] && ring[0][1] === ring.at(-1)![1] ? ring : [...ring, ring[0]];
}

test("test_ts_matches_python_baseline", async () => {
  expect(baseline.records).toHaveLength(15);
  const rows: string[] = ["| PNG | Python vertices | TS vertices | Hausdorff mm (upper bound) | Area delta % | TS vs truth mm (advisory) |", "|---|---:|---:|---:|---:|---:|"];
  const distances: number[] = [];
  for (const record of baseline.records) {
    if (record.result === "error") {
      await expect(capture(bytes(record.png))).rejects.toBeInstanceOf(DetectionError);
      await expect(capture(bytes(record.png))).rejects.toThrow(record.error!);
      try { await capture(bytes(record.png)); } catch (error) { expect((error as Error).message).toBe(record.error); }
      rows.push(`| ${record.png} | — | — | ${record.error} | — | — |`);
      continue;
    }
    const actual = await capture(bytes(record.png));
    const py = parse(record.footprint!), ts = parse(actual.footprint);
    expect(actual.grid.kind, record.png).toBe(record.kind);
    const distance = hausdorff(py, ts);
    const delta = Math.abs(area(ts) - area(py)) / area(py) * 100;
    const truthDistance = hausdorff(ts, closed(record.truth_mm));
    distances.push(distance);
    rows.push(`| ${record.png} | ${record.vertices} | ${ts.length - 1} | ${distance.toFixed(4)} | ${delta.toFixed(4)} | ${truthDistance.toFixed(4)} |`);
    expect(distance, record.png).toBeLessThanOrEqual(.6);
    expect(delta, record.png).toBeLessThanOrEqual(1);
  }
  expect(distances).toHaveLength(13);
  expect(distances.reduce((a, b) => a + b, 0) / distances.length).toBeLessThanOrEqual(.3);
  if (process.env.CAPTURE_PARITY_TABLE) writeFileSync(process.env.CAPTURE_PARITY_TABLE, rows.join("\n") + "\n");
}, 120_000);

test("test_encode_roundtrip_is_byte_identical", () => {
  const rows = baseline.records.filter(r => r.result === "footprint");
  expect(rows).toHaveLength(13);
  for (const r of rows) expect(encode(parse(r.footprint!))).toBe(r.footprint);
});

describe("test_validator_rejects_same_inputs", () => {
  // build123d/tests/test_capture_spike.py:139-156 + encoding.py:21-80.
  const vectors = [
    ["v2;0,0;10,0;10,10;0,0", "unsupported footprint version"],
    ["v1;0,0;10,0;10,10", "requires 3..256 vertices plus closing copy"],
    ["v1;0,0;10,0;10,10;0,10", "ring must be explicitly closed"],
    ["v1;0,0;2,0;2,2;0,0", "area must be at least 25 mm²"],
    ["v1;0,0;253,0;253,10;0,0", "footprint must fit 6x6 cells (252x252 mm)"],
    ["v1;0,0;10,10;0,10;10,0;0,0", "ring must be simple (no crossings or touches)"],
    ["v1;0,0;10,0;5,0;5,10;0,0", "overlapping adjacent edges"],
    ["v1;0,0;10,0;10,10;10,0;0,0", "repeated vertex"],
    ...["NaN", "1e2", "10.001", "10,0", "01", "+1", "1\n"].map(v =>
      [`v1;0,0;${v},0;10,10;0,0`, "coordinates require decimal mm with <=2 decimal places"]),
    ["v1;" + "0".repeat(16384), "encoding must be a string of at most 16 KB"],
    ["v1;1000001,0;1000011,0;1000011,10;1000001,0", "coordinate magnitude exceeds 1000000 mm"],
    ["v1;0,0;10,0;10,10;5,0;0,10;0,0", "ring must be simple (no crossings or touches)"],
  ];
  test.each(vectors)("vector %#", (wire, message) => {
    let caught: unknown;
    try { parse(wire); } catch (e) { caught = e; }
    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error).message).toBe(message);
  });
  test("quantization-degenerate ring", () => {
    expect(() => encode([[0, 0], [.001, 0], [10, 10], [0, 10], [0, 0]])).toThrow("repeated vertex");
  });
  test("256 distinct vertices and 252 mm span are inclusive", () => {
    const circle = (n: number): Point[] => {
      const p = Array.from({ length: n }, (_, i) => [100 + 50 * Math.cos(i * 2 * Math.PI / n), 100 + 50 * Math.sin(i * 2 * Math.PI / n)] as Point);
      return [...p, p[0]];
    };
    expect(parse(encode(circle(256)))).toHaveLength(257);
    expect(() => encode(circle(257))).toThrow("requires 3..256 vertices plus closing copy");
    expect(validate([[0, 0], [252, 0], [252, 252], [0, 252], [0, 0]])).toHaveLength(5);
    expect(() => validate([[0, 0], [10, 0], [Infinity, 10], [0, 0]])).toThrow("coordinates must be finite pairs");
  });
  test("Python binary rounding, ties to even and signed zero", () => {
    expect(encode([[-0, .125], [10.125, .125], [10.125, 10.375], [-0, .125]]))
      .toBe("v1;-0.00,0.12;10.12,0.12;10.12,10.38;-0.00,0.12");
    expect(encode([[.005, 2.675], [10.005, 2.675], [10.005, 12.675], [.005, 2.675]]))
      .toBe("v1;0.01,2.67;10.01,2.67;10.01,12.68;0.01,2.67");
  });
});

test("test_baseline_has_no_aruco_records", () => {
  // ArUco dropped: capture-bins-spike.md:102-108; build capability concern :54-55.
  expect(baseline.records).toHaveLength(15);
  expect(baseline.records.some(r => r.png.includes("aruco"))).toBe(false);
});

test("test_vendored_opencv_exposes_required_functions", async () => {
  const first = loadOpenCV();
  expect(loadOpenCV()).toBe(first);
  const cv = await first;
  const functions = ["Mat", "MatVector", "Size", "matFromArray", "cvtColor", "threshold", "findContours",
    "contourArea", "arcLength", "approxPolyDP", "getPerspectiveTransform", "warpPerspective",
    "boundingRect", "convexHull", "morphologyEx", "getBuildInformation"] as const;
  for (const name of functions) expect(typeof cv[name], name).toBe("function");
  expect(typeof cv.Mat.ones).toBe("function");
  expect(cv.getBuildInformation()).toMatch(/OpenCV 5\.0\.0/);
});

test("test_no_static_opencv_import", () => {
  const dir = path.join(process.cwd(), "lib/capture");
  const vendorPath = ["vendor", "opencv"].join("/");
  for (const file of readdirSync(dir).filter(f => f.endsWith(".ts") && !f.endsWith(".test.ts"))) {
    const source = readFileSync(path.join(dir, file), "utf8");
    expect(source).not.toMatch(/(?:import|export)\s+[\s\S]*?from\s*["'][^"']*opencv\.js/);
    if (file === "opencv.ts") {
      const beforeLoader = source.split("export function loadOpenCV")[0];
      expect(beforeLoader).not.toContain(vendorPath);
    } else expect(source).not.toContain(vendorPath);
  }
});

test("node decoding is RGB and supports Blob", async () => {
  const buffer = bytes("label-p0-bare-t0.png");
  const a = await decodeImage(buffer), b = await decodeImage(new Blob([buffer]));
  expect([a.width, a.height]).toEqual([b.width, b.height]);
  expect(Buffer.compare(a.data, b.data)).toBe(0);
  const { PNG } = await import("pngjs");
  const png = PNG.sync.read(Buffer.from(buffer));
  for (let i = 0; i < a.width * a.height; i++) {
    if (png.data[4 * i] !== png.data[4 * i + 2]) {
      expect(Array.from(a.data.subarray(i * 3, i * 3 + 3))).toEqual(Array.from(png.data.subarray(i * 4, i * 4 + 3)));
      return;
    }
  }
  throw new Error("fixture needs a non-neutral pixel");
});

test("uncropped rectify retains negative origin and both sample endpoints", async () => {
  const cv = await loadOpenCV();
  const image = { width: 120, height: 100, data: new Uint8Array(120 * 100 * 3).fill(180) };
  const r = rectify(cv, image, [.2, 0, -3, 0, .2, -2, 0, 0, 1]);
  expect(r.originMm).toEqual([-3, -2]);
  expect([r.image.width, r.image.height]).toEqual([120, 100]);
  expect(r.image.data).toEqual(image.data);
});

test("perimeter rejects low contrast and unsupported periods verbatim", () => {
  expect(() => periodCount(new Array(840).fill(180))).toThrow("no perimeter lattice contrast");
  expect(() => periodCount(Array.from({ length: 840 }, (_, i) => 100 * Math.sin(i * i)))).toThrow("perimeter does not support a 42 mm lattice");
});

test("custom resolution preserves Python ties-to-even rim inset", async () => {
  const cv = await loadOpenCV();
  const mask = segment(cv, {
    image: { width: 10, height: 10, data: new Uint8Array(300) },
    mmPerPx: 1.2, originMm: [0, 0], kind: "lattice", polarity: "pale",
  });
  // round(3 / 1.2) == 2 in Python, whereas Math.round would produce 3.
  expect(mask.data[2 * 10 + 2]).toBe(1);
  expect(mask.data[1 * 10 + 1]).toBe(0);
});


test("test_real_photo_parity", async () => {
  expect(baseline.records.length + real.records.length).toBe(17);
  const cv = await loadOpenCV(), distances: number[] = [];
  for (const record of real.records) {
    const input = bytes(`real/${record.png}`);
    if (record.kind) {
      const grid = detectGrid(cv, await decodeImage(input));
      expect(grid.kind).toBe(record.kind);
      expect(grid.polarity).toBe(record.polarity);
      expect(grid.sizeMm).toEqual([168,168]);
      expect(grid.confidence).toBeGreaterThanOrEqual(.5);
    }
    if (record.result === "error") {
      try { await capture(input); expect.fail(`expected ${record.error}`); }
      catch (error) { expect(error).toBeInstanceOf(DetectionError); expect((error as Error).message).toBe(record.error); }
    } else {
      const actual = await capture(input);
      const distance = hausdorff(parse(record.footprint!),actual.ring);
      distances.push(distance);
      expect(distance).toBeLessThanOrEqual(.6);
    }
  }
  if (distances.length) expect(distances.reduce((a,b) => a+b,0)/distances.length).toBeLessThanOrEqual(.3);
}, 120_000);

function skeletonImage(illumination = false) {
  const width = 768, data = new Uint8Array(width * width * 3).fill(220);
  const fill = (x0: number, y0: number, x1: number, y1: number, value: number) => {
    for (let y = y0; y < y1; y++) data.fill(value, (y * width + x0) * 3, (y * width + x1) * 3);
  };
  fill(48,48,720,720,30);
  for (let row = 0; row < 4; row++) for (let col = 0; col < 4; col++) {
    const x = 48+168*col, y = 48+168*row;
    fill(x+44,y+9,x+124,y+159,210); fill(x+9,y+44,x+159,y+124,210);
  }
  fill(320,340,440,388,248);
  if (illumination) for (let iy=0;iy<4;iy++) for (let ix=0;ix<4;ix++) {
    for (let y=48+iy*168;y<48+(iy+1)*168;y++) for (let x=48+ix*168;x<48+(ix+1)*168;x++)
      for (let c=0;c<3;c++) {
        const i=(y*width+x)*3+c;
        data[i]=Math.min(255,Math.max(0,data[i]*(.65+.1*iy+.025*ix)+3*ix));
      }
  }
  return { width, height: width, data };
}

test("test_structural_white_item_and_parameter_endpoints", async () => {
  const cv = await loadOpenCV(), image = skeletonImage();
  for (const floor of [.3,.8]) expect(detectGrid(cv,image,floor).polarity).toBe("dark");
  const grid = detectGrid(cv,image);
  const rect = rectify(cv,image,grid.H,{sizeMm:grid.sizeMm,kind:grid.kind,polarity:grid.polarity});
  for (const options of [{}, {k:3}, {k:8}, {coverageLimit:.2}, {coverageLimit:.5}, {shiftTolerance:1}, {shiftTolerance:3}]) {
    const mask = segment(cv,rect,options), ring = footprint(cv,mask);
    if (!Object.keys(options).length) expect(hausdorff(ring,structuralOracle.plain.ring)).toBeLessThanOrEqual(.3);
    const sides = [0,1].map(axis => Math.max(...ring.map(p=>p[axis]))-Math.min(...ring.map(p=>p[axis])));
    expect(Math.abs(sides[0]-30)).toBeLessThanOrEqual(1);
    expect(Math.abs(sides[1]-12)).toBeLessThanOrEqual(1);
    expect(mask.data.reduce((a,b)=>a+b,0)/mask.roi!.reduce((a,b)=>a+b,0)).toBeLessThan(.1);
  }
},120_000);


test("structural illumination fit retains light and dark background inliers", async () => {
  const cv=await loadOpenCV(), image=skeletonImage(true), grid=detectGrid(cv,image);
  const rect=rectify(cv,image,grid.H,{sizeMm:grid.sizeMm,polarity:grid.polarity});
  const mask=segment(cv,rect), ring=footprint(cv,mask);
  expect(hausdorff(ring,structuralOracle.illuminated.ring)).toBeLessThanOrEqual(.3);
  const sides=[0,1].map(axis=>Math.max(...ring.map(p=>p[axis]))-Math.min(...ring.map(p=>p[axis])));
  expect(Math.abs(sides[0]-30)).toBeLessThanOrEqual(1);
  expect(Math.abs(sides[1]-12)).toBeLessThanOrEqual(1);
  expect(mask.data.reduce((a,b)=>a+b,0)/mask.roi!.reduce((a,b)=>a+b,0)).toBeLessThan(.1);
},30_000);

test("structural coverage sanity raises its named error", async () => {
  const cv = await loadOpenCV(), image = await decodeImage(bytes("real/sharpie-daylight.png"));
  const grid = detectGrid(cv,image), rect = rectify(cv,image,grid.H,{sizeMm:grid.sizeMm,polarity:grid.polarity});
  expect(() => segment(cv,rect,{k:3,shiftTolerance:3})).toThrow("item too large for the plate or background not modelled");
},30_000);
