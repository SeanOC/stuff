// @vitest-environment jsdom

// Parity guard (pst-6ram): the build123d GLB detail page shows the same
// orientation compass the SCAD viewer has, and it tracks the live camera.
// GlbViewer touches WebGL/GLTFLoader on mount, which jsdom can't run, so
// it's stubbed to a marker that captures onCameraChange — letting the
// test drive the OrbitControls 'change' path from the outside, exactly
// like ViewerChrome.test does for StlViewer.

import { act, cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import BdDetailPage, { type BdDetailPageModel, viewFor } from "./BdDetailPage";
import type { CameraAxes } from "./StlViewer";

let mockOnCameraChange: ((axes: CameraAxes) => void) | null = null;
vi.mock("./GlbViewer", () => ({
  __esModule: true,
  default: ({
    onCameraChange,
    view,
  }: {
    onCameraChange?: (axes: CameraAxes) => void;
    view?: string;
  }) => {
    mockOnCameraChange = onCameraChange ?? null;
    return <div data-testid="glb-viewer" data-view={view ?? "iso"} />;
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

// Labels L4 (pst-egc3j): the text param joins the explicit Update/Enter
// flow (no render per keystroke), a render's 400 shows under the text row,
// and the 3MF download is offered only for a multi-colour model.
const LABEL: BdDetailPageModel = {
  slug: "holder-label-card",
  title: "Label card",
  blurb: "A card.",
  params: [
    {
      name: "text",
      kind: "string",
      label: "Label text",
      default: "Filament",
      maxLength: 24,
      charset: "printable-ascii",
    },
  ],
  presets: [{ id: "inlaid", label: "Inlaid", values: {} }],
  multiColour: true,
};

describe("BdDetailPage label text + 3MF", () => {
  afterEach(() => vi.restoreAllMocks());

  it("offers the 3MF download only for a multi-colour model", () => {
    const label = render(<BdDetailPage model={LABEL} />);
    expect(label.getByTestId("bd-download-3mf").textContent).toBe("Download 3MF (multi-colour)");
    expect(label.getByTestId("bd-download-stl")).toBeTruthy();
    cleanup();
    const plain = render(<BdDetailPage model={MODEL} />);
    expect(plain.queryByTestId("bd-download-3mf")).toBeNull();
    expect(plain.getByTestId("bd-download-stl")).toBeTruthy();
  });

  it("typing never renders; Enter renders once and a 400 shows under the row", async () => {
    const message = "label text 'WWWW' is too long for a 60 x 14 mm card: below the 1.2 mm floor";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: message }), {
        status: 400,
        headers: { "content-type": "application/json" },
      }),
    );
    const { getByLabelText, findByTestId } = render(<BdDetailPage model={LABEL} />);
    const input = getByLabelText("Label text") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "W".repeat(24) } });
    fireEvent.change(input, { target: { value: "W".repeat(23) } });
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.keyDown(input, { key: "Enter" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/bd-render");
    expect(JSON.parse(String((init as RequestInit).body)).params.text).toBe("W".repeat(23));
    expect((await findByTestId("param-error-text")).textContent).toBe(message);
  });

  it("the 3MF button downloads the live params as <slug>.3mf", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(new Uint8Array([0x50, 0x4b]), { status: 200 }));
    URL.createObjectURL = vi.fn(() => "blob:x");
    URL.revokeObjectURL = vi.fn();
    const clicked: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push(this.download);
    });
    const { getByLabelText, getByTestId } = render(<BdDetailPage model={LABEL} />);
    fireEvent.change(getByLabelText("Label text"), { target: { value: "PLA" } });
    await act(async () => {
      fireEvent.click(getByTestId("bd-download-3mf"));
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/bd-render?format=3mf");
    expect(JSON.parse(String((init as RequestInit).body)).params.text).toBe("PLA");
    expect(clicked).toEqual(["holder-label-card.3mf"]);
  });
});

describe("BdDetailPage camera hint (pst-5b83s)", () => {
  const CARD: BdDetailPageModel = {
    ...LABEL,
    params: [
      ...LABEL.params,
      { name: "text_style", kind: "enum", default: "inlaid", choices: ["inlaid", "raised"] },
    ],
    presets: [
      { id: "inlaid", label: "Inlaid", values: { text: "Filament", text_style: "inlaid" },
        defaultView: "bottom" },
      { id: "raised", label: "Raised", values: { text: "Filament", text_style: "raised" } },
    ],
  };
  const [inlaid, raised] = CARD.presets;

  it("opens the hinted preset on its text face and the others at iso", () => {
    const page = render(<BdDetailPage model={CARD} />);
    expect(page.getByTestId("glb-viewer").getAttribute("data-view")).toBe("bottom");
    fireEvent.click(page.getByTestId("bd-preset-raised"));
    expect(page.getByTestId("glb-viewer").getAttribute("data-view")).toBe("iso");
    cleanup();
    expect(render(<BdDetailPage model={MODEL} />).getByTestId("glb-viewer")
      .getAttribute("data-view")).toBe("iso");
  });

  it("a live render keeps the hint across text edits, not a style switch", () => {
    expect(viewFor(inlaid, CARD.params, null)).toBe("bottom");
    expect(viewFor(inlaid, CARD.params, { text: "PETG-CF", text_style: "inlaid" })).toBe("bottom");
    expect(viewFor(inlaid, CARD.params, { text: "PETG-CF", text_style: "raised" })).toBeUndefined();
    expect(viewFor(raised, CARD.params, null)).toBeUndefined();
  });
});
