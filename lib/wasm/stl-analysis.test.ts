import { describe, expect, it } from "vitest";
import {
  connectedComponentCount,
  isWatertight,
  parseStlTriangles,
  type Vec3,
} from "./stl-analysis";

// A closed tetrahedron at `offset` — the smallest watertight mesh.
function tetraAscii(offset: Vec3): string {
  const [ox, oy, oz] = offset;
  const A: Vec3 = [ox, oy, oz];
  const B: Vec3 = [ox + 1, oy, oz];
  const C: Vec3 = [ox, oy + 1, oz];
  const D: Vec3 = [ox, oy, oz + 1];
  const faces: [Vec3, Vec3, Vec3][] = [
    [A, B, C],
    [A, B, D],
    [A, C, D],
    [B, C, D],
  ];
  return faces
    .map(
      (f) =>
        `facet normal 0 0 0\nouter loop\n${f
          .map((v) => `vertex ${v[0]} ${v[1]} ${v[2]}`)
          .join("\n")}\nendloop\nendfacet`,
    )
    .join("\n");
}

function ascii(body: string): Uint8Array {
  return new TextEncoder().encode(`solid t\n${body}\nendsolid t\n`);
}

describe("parseStlTriangles", () => {
  it("parses ASCII facets", () => {
    const tris = parseStlTriangles(ascii(tetraAscii([0, 0, 0])));
    expect(tris).toHaveLength(4);
    expect(tris[0].vertices[1]).toEqual([1, 0, 0]);
  });

  it("parses binary STL by the byte-length identity", () => {
    const bytes = new Uint8Array(84 + 50);
    const dv = new DataView(bytes.buffer);
    dv.setUint32(80, 1, true);
    // One triangle: (0,0,0) (2,0,0) (0,3,0)
    dv.setFloat32(84 + 12 + 12, 2, true);
    dv.setFloat32(84 + 12 + 24 + 4, 3, true);
    const tris = parseStlTriangles(bytes);
    expect(tris).toHaveLength(1);
    expect(tris[0].vertices).toEqual([
      [0, 0, 0],
      [2, 0, 0],
      [0, 3, 0],
    ]);
  });

  it("returns empty for malformed input", () => {
    expect(parseStlTriangles(new Uint8Array([1, 2, 3]))).toEqual([]);
  });
});

describe("connectedComponentCount", () => {
  it("counts one component for a single solid", () => {
    const tris = parseStlTriangles(ascii(tetraAscii([0, 0, 0])));
    expect(connectedComponentCount(tris)).toBe(1);
  });

  it("counts disjoint solids separately", () => {
    const two = ascii(`${tetraAscii([0, 0, 0])}\n${tetraAscii([10, 0, 0])}`);
    expect(connectedComponentCount(parseStlTriangles(two))).toBe(2);
  });

  it("treats vertex-sharing triangles as connected", () => {
    const body = `facet normal 0 0 0\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet
facet normal 0 0 0\nouter loop\nvertex 0 0 0\nvertex -1 0 0\nvertex 0 -1 0\nendloop\nendfacet`;
    expect(connectedComponentCount(parseStlTriangles(ascii(body)))).toBe(1);
  });

  it("returns zero for an empty mesh", () => {
    expect(connectedComponentCount([])).toBe(0);
  });
});

describe("isWatertight", () => {
  it("accepts a closed tetrahedron", () => {
    expect(isWatertight(parseStlTriangles(ascii(tetraAscii([0, 0, 0]))))).toBe(true);
  });

  it("accepts two disjoint closed solids", () => {
    const two = ascii(`${tetraAscii([0, 0, 0])}\n${tetraAscii([10, 0, 0])}`);
    expect(isWatertight(parseStlTriangles(two))).toBe(true);
  });

  it("rejects an open mesh (lone triangle)", () => {
    const body = `facet normal 0 0 0\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet`;
    expect(isWatertight(parseStlTriangles(ascii(body)))).toBe(false);
  });

  it("rejects an empty mesh", () => {
    expect(isWatertight([])).toBe(false);
  });
});
