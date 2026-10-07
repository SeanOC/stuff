/** Wire contract: build123d/capture/encoding.py:7-80.
 * Limits: 256 vertices (:7,22), 16 KiB (:8,65,71), magnitude 1e6 (:31),
 * span 252 (:34-35), area >=25 (:56), 0.01 mm quantization (:61).
 * Validation order and messages deliberately match Python (:21-80).
 */
export type Point = [number, number];
export const MAX_VERTICES = 256;
export const MAX_BYTES = 16 * 1024;
const NUMBER = /^-?(?:0|[1-9]\d*)(?:\.\d{1,2})?$/;
const same = (a: Point, b: Point) => a[0] === b[0] && a[1] === b[1];
const cross = (a: Point, b: Point, c: Point) =>
  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
const on = (a: Point, b: Point, c: Point) => cross(a, b, c) === 0 &&
  [0, 1].every(k => Math.min(a[k], b[k]) <= c[k] && c[k] <= Math.max(a[k], b[k]));

export function area(ring: Point[]): number {
  return Math.abs(ring.slice(0, -1).reduce((s, a, i) => {
    const b = ring[i + 1];
    return s + a[0] * b[1] - a[1] * b[0];
  }, 0)) / 2;
}

export function validate(points: Point[]): Point[] {
  if (!Array.isArray(points)) throw new Error("coordinates must be finite pairs");
  if (points.length < 4 || points.length > MAX_VERTICES + 1)
    throw new Error("requires 3..256 vertices plus closing copy");
  if (points.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(Number.isFinite)))
    throw new Error("coordinates must be finite pairs");
  const p = points.map(xy => [...xy] as Point);
  if (!same(p[0], p[p.length - 1])) throw new Error("ring must be explicitly closed");
  if (new Set(p.slice(0, -1).map(xy => xy.join(","))).size !== p.length - 1)
    throw new Error("repeated vertex");
  if (p.some(xy => xy.some(v => Math.abs(v) > 1e6)))
    throw new Error("coordinate magnitude exceeds 1000000 mm");
  for (const k of [0, 1]) {
    if (Math.max(...p.map(xy => xy[k])) - Math.min(...p.map(xy => xy[k])) > 252)
      throw new Error("footprint must fit 6x6 cells (252x252 mm)");
  }
  for (let i = 0; i < p.length - 1; i++) {
    const a = p[i], b = p[i + 1], next = p[(i + 2) % (p.length - 1)];
    if (cross(a, b, next) === 0 && (on(a, b, next) || on(b, next, a)))
      throw new Error("overlapping adjacent edges");
    for (let j = i + 2; j < p.length - 1; j++) {
      if (i === 0 && j === p.length - 2) continue;
      const c = p[j], d = p[j + 1];
      if ((cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0) ||
          on(a, b, c) || on(a, b, d) || on(c, d, a) || on(c, d, b))
        throw new Error("ring must be simple (no crossings or touches)");
    }
  }
  if (area(p) < 25) throw new Error("area must be at least 25 mm²");
  return p;
}

// toFixed rounds the exact binary float at two decimal places, as Python does.
// Exact halfway values use ties-to-even (e.g. .125 -> .12); preserve signed zero.
function decimal(value: number): string {
  if (!Number.isFinite(value)) throw new Error("coordinates must be finite pairs");
  const absolute = Math.abs(value);
  let rounded = absolute.toFixed(2);
  const scaled = absolute * 100;
  if (absolute * 8 === Math.trunc(absolute * 8) && scaled % 1 === .5) {
    const lower = Math.floor(scaled);
    rounded = ((lower % 2 === 0 ? lower : lower + 1) / 100).toFixed(2);
  }
  return (value < 0 || Object.is(value, -0) ? "-" : "") + rounded;
}

export function encode(points: Point[]): string {
  const fields = points.map(([x, y]) => [decimal(x), decimal(y)]);
  validate(fields.map(([x, y]) => [Number(x), Number(y)]));
  const wire = "v1;" + fields.map(xy => xy.join(",")).join(";");
  if (new TextEncoder().encode(wire).length > MAX_BYTES) throw new Error("encoding exceeds 16 KB");
  return wire;
}

export function parse(value: string): Point[] {
  if (typeof value !== "string" || new TextEncoder().encode(value).length > MAX_BYTES)
    throw new Error("encoding must be a string of at most 16 KB");
  const [version, ...fields] = value.split(";");
  if (version !== "v1") throw new Error("unsupported footprint version");
  return validate(fields.map(field => {
    const xy = field.split(",");
    if (xy.length !== 2 || !xy.every(v => NUMBER.test(v) && !v.endsWith("\n")))
      throw new Error("coordinates require decimal mm with <=2 decimal places");
    return xy.map(Number) as Point;
  }));
}
