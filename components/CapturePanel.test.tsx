// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import BdDetailPage, { type BdDetailPageModel } from "./BdDetailPage";
import { DETECTION_ADVICE, photoPoint } from "./CapturePanel";
import { capture } from "@/lib/capture";
import { DETECTION_ERRORS, DetectionError } from "@/lib/capture/errors";

vi.mock("@/lib/capture", () => ({ capture: vi.fn() }));
vi.mock("./GlbViewer", () => ({ default: () => <div data-testid="viewer" /> }));

const MODEL: BdDetailPageModel = {
  slug: "gridfinity-capture-bin", title: "Capture bin", blurb: "A bin", capture: true,
  params: [
    { name: "footprint", kind: "string", default: "old", label: "Item footprint" },
    { name: "clearance", kind: "number", default: 1.6, min: 1, max: 3, step: .1 },
  ],
  presets: [{ id: "default", label: "Default", values: {} }],
};
const RESULT = {
  footprint: "v1;0,0;40,0;40,40;0,40;0,0",
  ring: [[0, 0], [40, 0], [40, 40], [0, 40], [0, 0]],
  grid: { H: [1, 0, 0, 0, 1, 0, 0, 0, 1], sizeMm: [84, 84], kind: "lattice", confidence: 1 },
} as Awaited<ReturnType<typeof capture>>;
const draw = { drawImage: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn() };
const close = vi.fn();

beforeEach(() => {
  vi.mocked(capture).mockReset().mockResolvedValue(RESULT);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(draw as unknown as ReturnType<HTMLCanvasElement["getContext"]>);
  vi.stubGlobal("createImageBitmap", vi.fn().mockResolvedValue({ width: 200, height: 200, close }));
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(new Uint8Array([1]), { status: 200 }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.clearAllMocks(); });

function choose(name = "item.png") {
  fireEvent.change(screen.getByLabelText("Take or choose a photo"), {
    target: { files: [new File(["photo"], name, { type: "image/png" })] },
  });
}

it("only mounts the panel for capture models and does not detect on mount", () => {
  const view = render(<BdDetailPage model={{ ...MODEL, capture: undefined }} />);
  expect(screen.queryByRole("heading", { name: "Capture an item outline" })).toBeNull();
  view.rerender(<BdDetailPage model={MODEL} />);
  expect(screen.getByRole("heading", { name: "Capture an item outline" })).toBeTruthy();
  expect(capture).not.toHaveBeenCalled();
  expect(fetch).not.toHaveBeenCalled();
});

it("shares clearance with ParamRail and applies the new footprint in exactly one render", async () => {
  render(<BdDetailPage model={MODEL} />);
  const slider = screen.getByRole("slider", { name: /Pocket clearance/ });
  fireEvent.change(slider, { target: { value: "2.3" } });
  expect((document.querySelector("#param-clearance") as HTMLInputElement).value).toBe("2.3");
  fireEvent.change(document.querySelector("#param-clearance")!, { target: { value: "2.1" } });
  expect((slider as HTMLInputElement).value).toBe("2.1");
  choose();
  expect(screen.getByRole("status").textContent).toBe("loading detector…");
  await waitFor(() => expect((screen.getByRole("button", { name: "Apply footprint" }) as HTMLButtonElement).disabled).toBe(false));
  expect(draw.drawImage).toHaveBeenCalledTimes(1);
  expect(draw.stroke).toHaveBeenCalledTimes(7); // three lattice lines per axis, one ring
  expect(close).toHaveBeenCalledOnce();
  expect(fetch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Apply footprint" }));
  await waitFor(() => expect(screen.getByTestId("bd-detail-root").getAttribute("data-bd-render-state")).toBe("ready"));
  expect((screen.getByLabelText("Item footprint") as HTMLInputElement).value).toBe(RESULT.footprint);
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = vi.mocked(fetch).mock.calls[0];
  expect(url).toBe("/api/bd-render");
  expect(init?.method).toBe("POST");
  expect(JSON.parse(String(init?.body)).params).toEqual({ footprint: RESULT.footprint, clearance: 2.1 });
  await waitFor(() => expect(screen.getByTestId("bd-detail-root").getAttribute("data-bd-stale")).toBe("false"));
});

const ADVICE_CASES = [
  ["no perimeter lattice contrast", "Show the whole baseplate on a plain surface that contrasts with the plate."],
  ["no board boundary", "Show the whole baseplate on a plain surface that contrasts with the plate."],
  ["board boundary is not a visible rectangle", "Show the whole baseplate on a plain surface that contrasts with the plate."],
  ["perimeter does not support a 42 mm lattice", "Use a Gridfinity baseplate 2–6 cells per side."],
  ["board touches image edge", "Step back so the whole baseplate is inside the frame."],
  ["board obstructed by an object crossing its edge", "Remove anything crossing the plate edge."],
  ["item too large for the plate or background not modelled", "Use a bigger plate or move the item inside the grid."],
  ["item crosses the plate edge", "Move the item fully inside the baseplate."],
  ["no item contour", "The item must contrast with the plate (colour or brightness)."],
  ["contour cannot meet the 0.3 mm / 256 vertex contract", "Simplify the item's outline or move the camera closer."],
] as const;

it("pins advice for every DetectionError", () => {
  expect(DETECTION_ADVICE).toEqual(Object.fromEntries(ADVICE_CASES));
  expect(Object.keys(DETECTION_ADVICE).sort()).toEqual([...DETECTION_ERRORS].sort());
});

it.each(ADVICE_CASES)("shows verbatim %s followed by advice", async (message, advice) => {
  vi.mocked(capture).mockRejectedValue(new DetectionError(message));
  render(<BdDetailPage model={MODEL} />);
  choose();
  const alert = await screen.findByRole("alert");
  expect([...alert.querySelectorAll("p")].map(p => p.textContent)).toEqual([message, advice]);
  expect((screen.getByRole("button", { name: "Apply footprint" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch).not.toHaveBeenCalled();
});

it("explains the encode span error", async () => {
  vi.mocked(capture).mockRejectedValue(new Error("footprint must fit 6x6 cells (252x252 mm)"));
  render(<BdDetailPage model={MODEL} />);
  choose();
  expect((await screen.findByRole("alert")).textContent).toBe("footprint must fit 6x6 cells (252x252 mm)The item is too large for a 6×6 bin.");
});

it("keeps server 400 routing under footprint and adds the size advice", async () => {
  const message = "footprint + wall exceeds 6x6 cells";
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ error: message }), { status: 400 }));
  render(<BdDetailPage model={MODEL} />);
  choose();
  await waitFor(() => expect((screen.getByRole("button", { name: "Apply footprint" }) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(screen.getByRole("button", { name: "Apply footprint" }));
  expect((await screen.findByTestId("param-error-footprint")).textContent)
    .toBe(`${message} Reduce clearance or wall_min, or pick a manual size.`);
});

it("ignores a superseded photo result and releases both bitmaps", async () => {
  let finish!: (result: typeof RESULT) => void;
  vi.mocked(capture).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  render(<BdDetailPage model={MODEL} />);
  choose("first.png");
  await waitFor(() => expect(capture).toHaveBeenCalledOnce());
  choose("second.png");
  await waitFor(() => expect((screen.getByRole("button", { name: "Apply footprint" }) as HTMLButtonElement).disabled).toBe(false));
  await act(async () => finish({ ...RESULT, footprint: "obsolete" }));
  fireEvent.click(screen.getByRole("button", { name: "Apply footprint" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  expect((screen.getByLabelText("Item footprint") as HTMLInputElement).value).toBe(RESULT.footprint);
  expect(close).toHaveBeenCalledTimes(2);
});

it("projects millimetre overlays back through a perspective homography", () => {
  const H = [2, .2, 10, .1, 3, 20, .001, .002, 1];
  const x = 100, y = 150, w = H[6] * x + H[7] * y + H[8];
  const result = photoPoint(H, [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w]);
  expect(result[0]).toBeCloseTo(x, 8);
  expect(result[1]).toBeCloseTo(y, 8);
});
