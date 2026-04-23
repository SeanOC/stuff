// @vitest-environment jsdom

// Guards the grid/model stacking contract (st-lpt): the grid must sit
// behind the StlViewer canvas so the model occludes it. With both the
// grid SVG and the viewer wrapper absolutely positioned, the later
// DOM sibling paints on top — so the grid must come first.
// Also covers the error-state UI (st-bg4).

import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ViewerChrome } from "./ViewerChrome";
import type { RenderResult, RenderState } from "@/hooks/useRenderer";

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

const ERROR_STATE: RenderState = {
  kind: "error",
  error: {
    line: 42,
    message: 'Parser error in file "test.scad", line 42: syntax error',
    log: "WARNING: blah\nERROR: Parser error in file \"test.scad\", line 42: syntax error\n",
  },
};

const LAST_GOOD: RenderResult = {
  stlBytes: new Uint8Array(84 + 50),
  triCount: 1,
  ms: 99,
};

describe("ViewerChrome error state (st-bg4)", () => {
  it("renders the error strip with message and line number", () => {
    const { getByTestId, getByText } = render(
      <ViewerChrome
        state={ERROR_STATE}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );
    const strip = getByTestId("error-strip");
    expect(strip.textContent).toContain("error");
    expect(strip.textContent).toContain("line 42");
    expect(strip.textContent).toContain("Parser error");
    expect(getByText("view full log")).toBeTruthy();
  });

  it("omits line label when RenderError.line is null", () => {
    const noLine: RenderState = {
      kind: "error",
      error: { line: null, message: "Unterminated comment block", log: "" },
    };
    const { getByTestId } = render(
      <ViewerChrome
        state={noLine}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );
    // The strip renders `line N` only when N is set; match the literal
    // "line " prefix of the label to avoid colliding with "multi-line"
    // or similar substrings inside the error message.
    expect(getByTestId("error-strip").textContent).not.toMatch(/\bline \d+\b/);
  });

  it("paints the last-good STL behind the error when history has one", () => {
    const { getByTestId } = render(
      <ViewerChrome
        state={ERROR_STATE}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
        history={[LAST_GOOD]}
      />,
    );
    expect(getByTestId("stl-viewer")).toBeTruthy();
  });

  it("opens the full-log modal on click and closes on backdrop click", () => {
    const { getByText, queryByTestId, getByTestId } = render(
      <ViewerChrome
        state={ERROR_STATE}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );
    expect(queryByTestId("error-log-modal")).toBeNull();

    fireEvent.click(getByText("view full log"));
    const modal = getByTestId("error-log-modal");
    expect(modal.textContent).toContain("Parser error");

    // Click the backdrop (the modal wrapper itself, not the dialog body).
    fireEvent.click(modal);
    expect(queryByTestId("error-log-modal")).toBeNull();
  });

  it("closes the full-log modal on Escape", () => {
    const { getByText, queryByTestId } = render(
      <ViewerChrome
        state={ERROR_STATE}
        camera="iso"
        showGrid={false}
        showDims={false}
        setCamera={() => {}}
        toggleGrid={() => {}}
        toggleDims={() => {}}
      />,
    );
    fireEvent.click(getByText("view full log"));
    expect(queryByTestId("error-log-modal")).toBeTruthy();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(queryByTestId("error-log-modal")).toBeNull();
  });
});
