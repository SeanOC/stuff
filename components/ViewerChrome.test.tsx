// @vitest-environment jsdom

// Guards the grid/model stacking contract (st-lpt): the grid must sit
// behind the StlViewer canvas so the model occludes it. With both the
// grid SVG and the viewer wrapper absolutely positioned, the later
// DOM sibling paints on top — so the grid must come first.
// Also covers the error-state UI (st-bg4).

import { cleanup, fireEvent, render as rtlRender } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ViewerChrome } from "./ViewerChrome";
import { UIProvider } from "@/contexts/UIContext";
import type { ReactElement } from "react";
import type { RenderResult, RenderState } from "@/hooks/useRenderer";

// ViewerChrome consumes UIContext (modal arbitration, errorLog dispatch).
// Every test renders inside a fresh UIProvider so the hook doesn't throw.
function render(ui: ReactElement) {
  return rtlRender(<UIProvider>{ui}</UIProvider>);
}

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
    dimensions: { x: 10, y: 10, z: 10 },
  },
};

const IDLE: RenderState = { kind: "idle" };

const commonProps = {
  camera: "iso" as const,
  showDims: false,
  setCamera: () => {},
  toggleGrid: () => {},
  toggleDims: () => {},
  onRefresh: () => {},
};

// The Modal component portals into #modal-root. Provide that target
// for every test; jsdom doesn't ship one by default.
beforeEach(() => {
  const root = document.createElement("div");
  root.id = "modal-root";
  document.body.appendChild(root);
});

afterEach(() => {
  cleanup();
  document.getElementById("modal-root")?.remove();
});

describe("ViewerChrome grid/model stacking", () => {
  it("renders GridOverlay before StlViewer in DOM order (grid is behind)", () => {
    const { getByTestId } = render(
      <ViewerChrome state={READY} showGrid {...commonProps} />,
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
      <ViewerChrome state={READY} showGrid={false} {...commonProps} />,
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
  dimensions: { x: 10, y: 10, z: 10 },
};

describe("ViewerChrome error state (st-bg4)", () => {
  it("renders the error strip with message and line number", () => {
    const { getByTestId, getByText } = render(
      <ViewerChrome state={ERROR_STATE} showGrid={false} {...commonProps} />,
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
      <ViewerChrome state={noLine} showGrid={false} {...commonProps} />,
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
        showGrid={false}
        {...commonProps}
        history={[LAST_GOOD]}
      />,
    );
    expect(getByTestId("stl-viewer")).toBeTruthy();
  });

  it("opens the full-log modal on click and closes on backdrop click", () => {
    const { getByText, queryByTestId, getByTestId } = render(
      <ViewerChrome state={ERROR_STATE} showGrid={false} {...commonProps} />,
    );
    expect(queryByTestId("error-log-modal")).toBeNull();

    fireEvent.click(getByText("view full log"));
    const modal = getByTestId("error-log-modal");
    expect(modal.textContent).toContain("Parser error");

    // The shared <Modal> puts its click-to-close handler on the
    // outer `role="presentation"` backdrop. Clicking the inner
    // dialog body (which carries the testid) deliberately does
    // NOT close the modal.
    const backdrop = document.querySelector('[role="presentation"]') as HTMLElement;
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop);
    expect(queryByTestId("error-log-modal")).toBeNull();
  });

  it("closes the full-log modal on Escape", () => {
    const { getByText, queryByTestId } = render(
      <ViewerChrome state={ERROR_STATE} showGrid={false} {...commonProps} />,
    );
    fireEvent.click(getByText("view full log"));
    expect(queryByTestId("error-log-modal")).toBeTruthy();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(queryByTestId("error-log-modal")).toBeNull();
  });
});

describe("ViewerChrome states (st-psn)", () => {
  it("shows the 'press ⏎ to render' hint in idle state", () => {
    const { getByTestId } = render(
      <ViewerChrome state={IDLE} showGrid={false} {...commonProps} />,
    );
    expect(getByTestId("press-enter-hint").textContent).toMatch(/press/i);
    expect(getByTestId("stat-strip-status").textContent).toMatch(/press/i);
  });

  it("calls onRefresh when Enter is pressed on the viewer section", () => {
    const onRefresh = vi.fn();
    const { getByLabelText } = render(
      <ViewerChrome
        state={IDLE}
        showGrid={false}
        {...commonProps}
        onRefresh={onRefresh}
      />,
    );
    const section = getByLabelText("3D preview");
    // fireEvent.focus dispatches through React's synthetic-event
    // system, which is what updates `focusInViewer` (the shortcut gate).
    // The raw `section.focus()` call used to flip tabIndex but not
    // React's state, so the gate stayed closed and Enter no-op'd.
    fireEvent.focus(section);
    fireEvent.keyDown(window, { key: "Enter" });
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("renders dimensions × tri × ms × kb on ready state", () => {
    const { getByTestId } = render(
      <ViewerChrome state={READY} showGrid={false} {...commonProps} />,
    );
    const dims = getByTestId("stat-strip-dimensions").textContent ?? "";
    expect(dims).toMatch(/10\.0\s*×\s*10\.0\s*×\s*10\.0\s*mm/);
    const strip = getByTestId("stat-strip").textContent ?? "";
    expect(strip).toMatch(/TRI\s*1/);
    expect(strip).toMatch(/MS\s*42/);
  });

  it("shows the indeterminate progress bar while loading", () => {
    const { getByTestId } = render(
      <ViewerChrome
        state={{ kind: "loading", since: 0 }}
        showGrid={false}
        {...commonProps}
      />,
    );
    expect(getByTestId("loading-progress")).toBeTruthy();
    expect(getByTestId("stat-strip-status").textContent).toMatch(/compil/i);
  });
});
