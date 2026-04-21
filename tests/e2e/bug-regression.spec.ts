import { expect, test } from "@playwright/test";

// Silent-override regression. If applyParamOverrides ever stops mutating
// the source (as happened with bare `-D` flags under
// openscad-wasm-prebuilt), this test fails because default and overridden
// renders produce identical STL bboxes — a visible, unambiguous failure
// where byte-count checks would not necessarily diverge.

const FIXTURE = "tests/fixtures/bug_regression.scad";

// Tiny ASCII STL parser — enough to extract the printed bbox from the
// facet vertex lines. Not a general STL parser; only handles ASCII
// `vertex X Y Z` lines, which is what openscad-wasm-prebuilt emits.
function bboxFromAsciiStl(stl: string): { min: [number, number, number]; max: [number, number, number] } {
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  const vertexRe = /vertex\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)/g;
  for (const m of stl.matchAll(vertexRe)) {
    const [x, y, z] = [Number(m[1]), Number(m[2]), Number(m[3])];
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
    if (z < minZ) minZ = z;
    if (z > maxZ) maxZ = z;
  }
  return { min: [minX, minY, minZ], max: [maxX, maxY, maxZ] };
}

async function exportStl(baseURL: string, params: Record<string, number>): Promise<string> {
  const res = await fetch(`${baseURL}/api/export`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model: FIXTURE, params }),
  });
  if (!res.ok) throw new Error(`export failed: ${res.status} ${await res.text()}`);
  return res.text();
}

test("param override shifts bbox in the rendered STL", async ({ baseURL }) => {
  if (!baseURL) throw new Error("baseURL missing");

  const defaultStl = await exportStl(baseURL, {});
  const widenedStl = await exportStl(baseURL, { width: 160 });

  const a = bboxFromAsciiStl(defaultStl);
  const b = bboxFromAsciiStl(widenedStl);

  // Default plate width = 40 (±20). Widened = 160 (±80). Under a silent
  // override bug, b matches a exactly and this assertion fails loudly.
  expect(a.max[0] - a.min[0]).toBeCloseTo(40, 0);
  expect(b.max[0] - b.min[0]).toBeCloseTo(160, 0);
  expect(b.max[0] - b.min[0]).toBeGreaterThan(a.max[0] - a.min[0] + 100);
});
