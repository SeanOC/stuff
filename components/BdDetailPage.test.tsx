// @vitest-environment jsdom

// Parity guard (pst-6ram): the build123d GLB detail page shows the same
// orientation compass the SCAD viewer has, and it tracks the live camera.
// GlbViewer touches WebGL/GLTFLoader on mount, which jsdom can't run, so
// it's stubbed to a marker that captures onCameraChange — letting the
// test drive the OrbitControls 'change' path from the outside, exactly
// like ViewerChrome.test does for StlViewer.

import { act, cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BdDetailPage, { type BdDetailPageModel } from "./BdDetailPage";
import type { CameraAxes } from "./StlViewer";

let mockOnCameraChange: ((axes: CameraAxes) => void) | null = null;
vi.mock("./GlbViewer", () => ({
  __esModule: true,
  default: ({
    onCameraChange,
  }: {
    onCameraChange?: (axes: CameraAxes) => void;
  }) => {
    mockOnCameraChange = onCameraChange ?? null;
    return <div data-testid="glb-viewer" />;
  },
}));

const MODEL: BdDetailPageModel = {
  slug: "holder-spray-can",
  title: "Spray Can Holder",
  blurb: "A holder.",
  params: [],
  presets: [{ id: "spray_can", label: "Spray Can", values: {} }],
};

afterEach(() => {
  cleanup();
  mockOnCameraChange = null;
});

function xAxisEndpoint(el: HTMLElement): { x2: string } {
  const x = el.querySelector('g[data-axis="x"] line') as SVGLineElement | null;
  if (!x) throw new Error("X-axis <line> not found in indicator SVG");
  return { x2: x.getAttribute("x2") ?? "" };
}

describe("BdDetailPage orientation compass", () => {
  it("renders the shared axes indicator on the GLB viewer", () => {
    const { getByTestId } = render(<BdDetailPage model={MODEL} />);
    const indicator = getByTestId("axes-indicator");
    // Reuses the SCAD compass component: same data-preset contract, iso
    // fallback before the first camera change arrives.
    expect(indicator.getAttribute("data-preset")).toBe("iso");
  });

  it("tracks the live camera once the GLB viewer emits", () => {
    const { getByTestId } = render(<BdDetailPage model={MODEL} />);
    const before = xAxisEndpoint(getByTestId("axes-indicator"));

    // Simulate GlbViewer's onCameraChange (fired on load + every orbit).
    // X along screen-right → x2 = cx + R = 26 + 22 = 48 exactly.
    act(() => {
      mockOnCameraChange?.({
        x: [1, 0, 0],
        y: [0, 0, 1],
        z: [0, 1, 0],
      });
    });

    const after = xAxisEndpoint(getByTestId("axes-indicator"));
    expect(parseFloat(after.x2)).toBeCloseTo(48, 1);
    expect(after.x2).not.toBe(before.x2);
  });
});
