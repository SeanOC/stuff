// @vitest-environment jsdom

// Guards the grid/model stacking contract (st-lpt): the grid must sit
// behind the StlViewer canvas so the model occludes it. With both the
// grid SVG and the viewer wrapper absolutely positioned, the later
// DOM sibling paints on top — so the grid must come first.

import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ViewerChrome } from "./ViewerChrome";
import type { RenderState } from "@/hooks/useRenderer";

// StlViewer touches WebGL on mount via three.js. jsdom has no WebGL.
// The stacking assertion only cares about DOM order, so stub the
// component to a labeled marker div.
vi.mock("./StlViewer", () => ({
  __esModule: true,
  default: () => <div data-testid="stl-viewer" />,
}));

const READY: RenderState = {
  kind: "ready",
  result: {
    stlBytes: new Uint8Array(84 + 50),
    triCount: 1,
    ms: 42,
  },
};

afterEach(() => cleanup());

describe("ViewerChrome grid/model stacking", () => {
  it("renders GridOverlay before StlViewer in DOM order (grid is behind)", () => {
    const { getByTestId } = render(
      <ViewerChrome
        state={READY}
        camera="iso"
        showGrid
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );

    const grid = getByTestId("viewer-grid");
    const viewer = getByTestId("stl-viewer");

    // Node.compareDocumentPosition returns a bitmask; DOCUMENT_POSITION_FOLLOWING
    // on the second node means grid precedes viewer — grid paints first.
    const pos = grid.compareDocumentPosition(viewer);
    expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("omits the grid when showGrid is false", () => {
    const { queryByTestId } = render(
      <ViewerChrome
        state={READY}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );
    expect(queryByTestId("viewer-grid")).toBeNull();
  });
});
