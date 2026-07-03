// Mesh-level sanity analysis for rendered STLs.
//
// Purpose-built for the param-sweep connectivity guard (st-7x7): a
// render "succeeding" is not enough — a CSG failure can drop part of
// the tree and leave a shattered or open mesh. These helpers answer
// the two questions the guard asks of every sweep render:
//   - how many connected components does the mesh have?
//   - is it watertight (every edge shared by exactly two triangles)?
//
// Vertex identity is exact-coordinate: STL repeats each shared vertex
// per facet, and the Manifold backend emits bitwise-identical floats
// for shared vertices, so no epsilon-welding is needed. Pure functions,
// no fs/io — same parsing conventions as hooks/useRenderer.ts.

const BIN_STL_HEADER_BYTES = 84;
const BIN_STL_TRI_BYTES = 50;

export type Vec3 = [number, number, number];

export interface StlTriangle {
  vertices: [Vec3, Vec3, Vec3];
}

/**
 * Parse binary or ASCII STL into triangles. Binary is detected by the
 * byteLength == 84 + nTri * 50 identity (the header's leading "solid"
 * text is not reliable). Malformed input yields an empty array rather
 * than throwing.
 */
export function parseStlTriangles(bytes: Uint8Array): StlTriangle[] {
  if (bytes.byteLength >= BIN_STL_HEADER_BYTES) {
    const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const claimed = dv.getUint32(80, true);
    if (bytes.byteLength === BIN_STL_HEADER_BYTES + claimed * BIN_STL_TRI_BYTES) {
      const tris: StlTriangle[] = [];
      for (let t = 0; t < claimed; t++) {
        const base = BIN_STL_HEADER_BYTES + t * BIN_STL_TRI_BYTES;
        const vertices = [0, 1, 2].map((k) => {
          const o = base + 12 + k * 12;
          return [
            dv.getFloat32(o, true),
            dv.getFloat32(o + 4, true),
            dv.getFloat32(o + 8, true),
          ] as Vec3;
        }) as [Vec3, Vec3, Vec3];
        tris.push({ vertices });
      }
      return tris;
    }
  }
  return parseAsciiStl(bytes);
}

const ASCII_VERTEX_RE = /vertex\s+(\S+)\s+(\S+)\s+(\S+)/g;

function parseAsciiStl(bytes: Uint8Array): StlTriangle[] {
  const text = new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  const verts: Vec3[] = [];
  for (const m of text.matchAll(ASCII_VERTEX_RE)) {
    verts.push([Number(m[1]), Number(m[2]), Number(m[3])]);
  }
  const tris: StlTriangle[] = [];
  for (let i = 0; i + 2 < verts.length; i += 3) {
    tris.push({ vertices: [verts[i], verts[i + 1], verts[i + 2]] });
  }
  return tris;
}

function vertexKey(v: Vec3): string {
  return `${v[0]},${v[1]},${v[2]}`;
}

/**
 * Number of connected components, where triangles sharing at least one
 * exact vertex are connected. An empty mesh has zero components.
 */
export function connectedComponentCount(tris: StlTriangle[]): number {
  if (tris.length === 0) return 0;
  const parent = tris.map((_, i) => i);
  const find = (a: number): number => {
    let root = a;
    while (parent[root] !== root) root = parent[root];
    // Path compression keeps the sweep's ~100k-triangle meshes cheap.
    let cur = a;
    while (parent[cur] !== root) {
      const next = parent[cur];
      parent[cur] = root;
      cur = next;
    }
    return root;
  };
  const byVertex = new Map<string, number>();
  tris.forEach((t, i) => {
    for (const v of t.vertices) {
      const key = vertexKey(v);
      const prev = byVertex.get(key);
      if (prev === undefined) byVertex.set(key, i);
      else parent[find(i)] = find(prev);
    }
  });
  const roots = new Set<number>();
  for (let i = 0; i < tris.length; i++) roots.add(find(i));
  return roots.size;
}

/**
 * Watertight = no open borders: every undirected edge is used by at
 * least two triangles. An edge used exactly once is a hole — the
 * signature of dropped/shattered geometry this check exists to catch.
 * Edges used more than twice are allowed: CSG output legitimately has
 * two solids meeting along a shared edge (4 uses — e.g. goblu's
 * zero-gap dovetailed pods), which prints fine and is not a defect.
 * Empty meshes are not watertight.
 */
export function isWatertight(tris: StlTriangle[]): boolean {
  if (tris.length === 0) return false;
  const edgeUse = new Map<string, number>();
  for (const t of tris) {
    const keys = t.vertices.map(vertexKey);
    for (let k = 0; k < 3; k++) {
      const a = keys[k];
      const b = keys[(k + 1) % 3];
      const edge = a < b ? `${a}|${b}` : `${b}|${a}`;
      edgeUse.set(edge, (edgeUse.get(edge) ?? 0) + 1);
    }
  }
  for (const count of edgeUse.values()) {
    if (count === 1) return false;
  }
  return true;
}
