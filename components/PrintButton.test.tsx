// @vitest-environment jsdom

// pst-62i6h: the Print button talks to the print bridge directly from the
// browser. Health gate, payload (preset vs params vs scad) and the
// 202 / 409 / 403 / 5xx rendering, all against a mocked fetch.

import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PrintButton, { POLL_CAP_MS, POLL_INTERVAL_MS } from "./PrintButton";
import BdDetailPage, { type BdDetailPageModel } from "./BdDetailPage";
import {
  bdPrintTarget,
  fetchPrinters,
  fetchRun,
  startPrint,
  probePrintBridge,
  READ_TIMEOUT_MS,
  PRINT_TIMEOUT_MS,
  resetPrintBridgeHealthCache,
  type PrintTarget,
} from "@/lib/print-bridge/client";

vi.mock("./GlbViewer", () => ({
  __esModule: true,
  default: () => <div data-testid="glb-viewer" />,
}));

const BRIDGE = "https://cubert.tail.ts.net:8443";

const PRINTERS = [
  { id: 1, name: "H2S", model: "H2S", state: "IDLE", plate_detection_calibrated: true, pipeline: "h2s", nozzle_mm: [0.6] },
  { id: 2, name: "Lefty", model: "H2C", state: "IDLE", plate_detection_calibrated: false, pipeline: "h2c", nozzle_mm: [] },
];

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

let fetchMock: ReturnType<typeof vi.fn>;
let printHandler: Handler;
let runHandler: Handler;
let healthHandler: Handler;
let printersHandler: Handler;

function calls(path: string, method = "GET"): [string, RequestInit | undefined][] {
  return (fetchMock.mock.calls as [string, RequestInit | undefined][]).filter(
    ([url, init]) => url === `${BRIDGE}${path}` && (init?.method ?? "GET") === method,
  );
}

function postedBody(): Record<string, unknown> {
  const posts = calls("/print", "POST");
  expect(posts).toHaveLength(1);
  return JSON.parse(String(posts[0][1]?.body));
}

beforeEach(() => {
  resetPrintBridgeHealthCache();
  vi.stubEnv("NEXT_PUBLIC_PRINT_BRIDGE_URL", BRIDGE);
  healthHandler = () => json({ ok: true, bambuddy_reachable: true });
  printersHandler = () => json(PRINTERS);
  printHandler = () => json({ library_file_id: 9, run_id: 42, status_url: "/runs/42" }, 202);
  runHandler = () => json({ status: "slicing", copies: 2, copies_completed: 0, copies_failed: 0 });
  fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === `${BRIDGE}/health`) return healthHandler(url, init);
    if (url === `${BRIDGE}/printers`) return printersHandler(url, init);
    if (url === `${BRIDGE}/print`) return printHandler(url, init);
    if (url.startsWith(`${BRIDGE}/runs/`)) return runHandler(url, init);
    return new Response("not found", { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

const BD_PRESET: PrintTarget = { source: "bd", slug: "holder-spray-can", preset: "spray_can" };

async function mount(target: PrintTarget = BD_PRESET) {
  const view = render(<PrintButton target={target} variant="rail" />);
  await act(async () => {});
  return view;
}

async function openAndPrint(copies?: number, printerId?: number) {
  await act(async () => {
    fireEvent.click(screen.getByTestId("print-button"));
  });
  if (printerId !== undefined) {
    fireEvent.change(screen.getByTestId("print-printer"), { target: { value: String(printerId) } });
  }
  if (copies !== undefined) {
    fireEvent.change(screen.getByTestId("print-copies"), { target: { value: String(copies) } });
  }
  await act(async () => {
    fireEvent.click(screen.getByTestId("print-submit"));
  });
}

describe("PrintButton health gate", () => {
  it("renders nothing and fetches nothing when the env var is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_PRINT_BRIDGE_URL", "");
    const { container } = await mount();
    expect(container.innerHTML).toBe("");
    await act(async () => { fireEvent(document, new Event("visibilitychange")); });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("mounts once /health reports ok and Bambuddy reachable", async () => {
    await mount();
    expect(screen.getByTestId("print-button")).toBeTruthy();
    expect(calls("/health")).toHaveLength(1);
  });

  it.each([
    ["Bambuddy unreachable", () => json({ ok: true, bambuddy_reachable: false })],
    ["HTTP error", () => json({ error: "nope" }, 500)],
    ["network failure", () => Promise.reject(new TypeError("Failed to fetch"))],
  ])("renders nothing on %s, with no error UI", async (_label, handler) => {
    healthHandler = handler as Handler;
    const { container } = await mount();
    expect(container.innerHTML).toBe("");
  });

  it("renders nothing when /health does not answer within 2 s", async () => {
    vi.useFakeTimers();
    healthHandler = (_url, init) =>
      new Promise((_resolve, reject) =>
        init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError"))),
      );
    const { container } = render(<PrintButton target={BD_PRESET} variant="rail" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_000);
    });
    expect(container.innerHTML).toBe("");
  });

  it("caches successful probes across remounts, visibility changes and opening", async () => {
    vi.useFakeTimers();
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    await mount();
    cleanup();
    await mount();
    await act(async () => {
      fireEvent(document, new Event("visibilitychange"));
      fireEvent.click(screen.getByTestId("print-button"));
    });
    expect(calls("/health")).toHaveLength(1);
  });

  it("re-probes a negative result when visible and mounts without reloading", async () => {
    vi.useFakeTimers();
    const visibility = vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    healthHandler = () => Promise.reject(new TypeError("Failed to fetch"));
    const { container } = await mount();
    expect(container.innerHTML).toBe("");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
      fireEvent(document, new Event("visibilitychange"));
    });
    expect(calls("/health")).toHaveLength(1);
    healthHandler = () => json({ ok: true, bambuddy_reachable: true });
    visibility.mockReturnValue("visible");
    await act(async () => { fireEvent(document, new Event("visibilitychange")); });
    expect(screen.getByTestId("print-button")).toBeTruthy();
    expect(calls("/health")).toHaveLength(2);
  });

  it("shares in-flight probes and forgets a failed probe on remount", async () => {
    let resolve!: (value: Response) => void;
    healthHandler = () => new Promise((done) => { resolve = done; });
    await mount();
    const secondProbe = probePrintBridge(BRIDGE);
    expect(calls("/health")).toHaveLength(1);
    await act(async () => {
      resolve(json({ ok: true, bambuddy_reachable: false }));
      expect(await secondProbe).toBe(false);
    });
    cleanup();
    healthHandler = () => json({ ok: true, bambuddy_reachable: true });
    await mount();
    expect(screen.getByTestId("print-button")).toBeTruthy();
    expect(calls("/health")).toHaveLength(2);
  });

  it("removes the visibility listener when unmounted", async () => {
    vi.spyOn(document, "visibilityState", "get").mockReturnValue("visible");
    healthHandler = () => Promise.reject(new TypeError("Failed to fetch"));
    const view = await mount();
    view.unmount();
    await act(async () => { fireEvent(document, new Event("visibilitychange")); });
    expect(calls("/health")).toHaveLength(1);
  });
});

describe("PrintButton popover + payload", () => {
  it("lists printers with the uncalibrated plate-check hint", async () => {
    await mount();
    await act(async () => {
      fireEvent.click(screen.getByTestId("print-button"));
    });
    const options = Array.from(
      (screen.getByTestId("print-printer") as HTMLSelectElement).options,
    ).map((o) => o.textContent);
    expect(options).toEqual(["H2S — H2S · 0.6 mm", "Lefty — H2C"]);
    expect(screen.queryByTestId("print-plate-hint")).toBeNull();
    fireEvent.change(screen.getByTestId("print-printer"), { target: { value: "2" } });
    expect(screen.getByTestId("print-plate-hint").textContent).toMatch(/not calibrated/i);
    const copies = Array.from((screen.getByTestId("print-copies") as HTMLSelectElement).options);
    expect(copies.map((o) => o.value)).toEqual(["1", "2", "3", "4", "5", "6", "7", "8", "9"]);
  });

  it("posts a bd preset target with printer and copies", async () => {
    await mount();
    await openAndPrint(3, 2);
    expect(postedBody()).toEqual({
      source: "bd",
      slug: "holder-spray-can",
      preset: "spray_can",
      printer_id: 2,
      copies: 3,
    });
  });

  it("posts bd params when the controls are not a manifest preset", async () => {
    await mount(bdPrintTarget("holder-spray-can", null, { width: 70 }));
    await openAndPrint();
    expect(postedBody()).toEqual({
      source: "bd",
      slug: "holder-spray-can",
      params: { width: 70 },
      printer_id: 1,
      copies: 1,
    });
  });

  it("posts a scad target as {model, params}", async () => {
    await mount({ source: "scad", model: "models/opengrid_bin.scad", params: { width_units: 2 } });
    await openAndPrint();
    expect(postedBody()).toEqual({
      source: "scad",
      model: "models/opengrid_bin.scad",
      params: { width_units: 2 },
      printer_id: 1,
      copies: 1,
    });
  });

  it("bdPrintTarget picks preset over params exactly when bakedPresetId is set", () => {
    expect(bdPrintTarget("s", "p1", { a: 1 })).toEqual({ source: "bd", slug: "s", preset: "p1" });
    expect(bdPrintTarget("s", null, { a: 1 })).toEqual({ source: "bd", slug: "s", params: { a: 1 } });
  });
});

describe("PrintButton responses", () => {
  it("202 → Queued on <printer>, polls /runs every 10 s until terminal", async () => {
    vi.useFakeTimers();
    let n = 0;
    runHandler = () => {
      n += 1;
      return n < 2
        ? json({ status: "in_progress", copies: 2, copies_completed: 1, copies_failed: 0 })
        : json({ status: "completed", copies: 2, copies_completed: 2, copies_failed: 0 });
    };
    render(<PrintButton target={BD_PRESET} variant="rail" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await openAndPrint();
    expect(screen.getByTestId("print-status").textContent).toContain("Queued on H2S");
    expect(calls("/runs/42")).toHaveLength(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    });
    expect(screen.getByTestId("print-run").textContent).toBe("in_progress · 1/2 done");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
    });
    expect(screen.getByTestId("print-run").textContent).toBe("completed · 2/2 done");
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
      });
    }
    expect(calls("/runs/42")).toHaveLength(2);
    expect(calls("/print", "POST")).toHaveLength(1);
  });

  it("an unknown status keeps polling, then stops at the cap showing the last status", async () => {
    vi.useFakeTimers();
    runHandler = () => json({ status: "mystery", copies: 1, copies_completed: 0, copies_failed: 0 });
    render(<PrintButton target={BD_PRESET} variant="rail" />);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    await openAndPrint();
    for (let t = 0; t <= POLL_CAP_MS; t += POLL_INTERVAL_MS) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
      });
    }
    const polled = calls("/runs/42").length;
    expect(polled).toBe(POLL_CAP_MS / POLL_INTERVAL_MS);
    expect(screen.getByTestId("print-gave-up")).toBeTruthy();
    expect(screen.getByTestId("print-run").textContent).toContain("mystery");
    for (let i = 0; i < 5; i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
      });
    }
    expect(calls("/runs/42")).toHaveLength(polled);
  });

  it("409 lists the eligibility issues verbatim", async () => {
    const issue = { kind: "filament_type_mismatch", slot_index: 0, expected: "PLA", actual: "PETG" };
    printHandler = () =>
      json(
        { error: "pipeline eligibility check failed", report: { ok: false, issues: [issue] } },
        409,
      );
    await mount();
    await openAndPrint();
    const box = screen.getByTestId("print-conflict");
    expect(box.textContent).toContain("pipeline eligibility check failed");
    expect(Array.from(box.querySelectorAll("li")).map((li) => li.textContent)).toEqual([
      JSON.stringify(issue),
    ]);
    expect(calls("/runs/42")).toHaveLength(0);
  });

  it.each([
    [403, { error: "Tailscale-User-Login is not the trusted login" }, /not the trusted login/],
    [502, { error: "Bambuddy unreachable: ConnectError" }, /^Bambuddy is unreachable from the print bridge\.$/],
    [502, { error: "another upstream failure" }, /^another upstream failure \(HTTP 502\)$/],
    [500, null, /HTTP 500/],
  ])("%i → one-line error, never re-posted", async (status, body, pattern) => {
    printHandler = () =>
      body ? json(body, status) : new Response("boom", { status });
    await mount();
    await openAndPrint();
    expect(screen.getByTestId("print-error").textContent).toMatch(pattern);
    expect(calls("/print", "POST")).toHaveLength(1);
  });
});

const NETWORK_MESSAGE = "Print bridge unreachable. Are you on the tailnet?";

/** Model a connection (or response body) that only settles on abort. */
const hangsUntilAbort: Handler = (_url, init) => new Promise((_resolve, reject) => {
  init?.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
});

describe("PrintButton connection recovery", () => {
  beforeEach(() => { vi.useFakeTimers(); });

  it.each([
    ["network failure", () => Promise.reject(new TypeError("Failed to fetch")), NETWORK_MESSAGE],
    ["Bambuddy failure", () => json({ error: "Bambuddy unreachable: ConnectError" }, 502),
      "Bambuddy is unreachable from the print bridge."],
  ])("shows a readable printers %s and Retry recovers", async (_label, handler, message) => {
    printersHandler = handler as Handler;
    await mount();
    await act(async () => { fireEvent.click(screen.getByTestId("print-button")); });
    expect(screen.getByTestId("print-printers-error").textContent).toBe(message);
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(calls("/printers")).toHaveLength(1);
    printersHandler = () => json(PRINTERS);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Retry" })); });
    expect(screen.queryByTestId("print-printers-error")).toBeNull();
    expect(screen.getByTestId("print-printer")).toBeTruthy();
    expect(calls("/printers")).toHaveLength(2);
  });

  it.each([new TypeError("Failed to fetch"), new DOMException("aborted", "AbortError")])(
    "a rejected submission stays usable without retrying the POST (%s)", async (error) => {
      printHandler = () => Promise.reject(error);
      await mount();
      await openAndPrint();
      expect(screen.getByTestId("print-error").textContent).toBe(NETWORK_MESSAGE);
      expect((screen.getByTestId("print-submit") as HTMLButtonElement).disabled).toBe(false);
      await act(async () => { await vi.advanceTimersByTimeAsync(PRINT_TIMEOUT_MS); });
      expect(calls("/print", "POST")).toHaveLength(1);
    },
  );

  it("times out printer loading with a usable Retry", async () => {
    printersHandler = hangsUntilAbort;
    await mount();
    await act(async () => { fireEvent.click(screen.getByTestId("print-button")); });
    await act(async () => { await vi.advanceTimersByTimeAsync(READ_TIMEOUT_MS - 1); });
    expect(screen.getByText("Loading printers…")).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(screen.getByTestId("print-printers-error").textContent).toBe(NETWORK_MESSAGE);
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("allows five minutes for a print, then re-enables the form without re-posting", async () => {
    printHandler = hangsUntilAbort;
    await mount();
    await openAndPrint();
    await act(async () => { await vi.advanceTimersByTimeAsync(PRINT_TIMEOUT_MS - 1); });
    expect(screen.getByText("Sending…")).toBeTruthy();
    await act(async () => { await vi.advanceTimersByTimeAsync(1); });
    expect(screen.getByTestId("print-error").textContent).toBe(NETWORK_MESSAGE);
    expect((screen.getByTestId("print-submit") as HTMLButtonElement).disabled).toBe(false);
    expect(calls("/print", "POST")).toHaveLength(1);
  });

  it("reports three consecutive poll failures, clears on success, and resets the count", async () => {
    await mount();
    await openAndPrint();
    const tick = () => act(async () => { await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS); });
    await tick();
    runHandler = () => Promise.reject(new TypeError("Failed to fetch"));
    for (let i = 0; i < 2; i++) {
      await tick();
      expect(screen.queryByTestId("print-lost-contact")).toBeNull();
    }
    await tick();
    expect(screen.getByTestId("print-lost-contact").textContent).toBe(
      "Lost contact with the print bridge; last status: slicing",
    );
    runHandler = () => json({ status: "printing" });
    await tick();
    expect(screen.queryByTestId("print-lost-contact")).toBeNull();
    expect(screen.getByTestId("print-run").textContent).toBe("printing");
    runHandler = () => Promise.reject(new TypeError("Failed to fetch"));
    await tick();
    expect(screen.queryByTestId("print-lost-contact")).toBeNull();
    expect(calls("/print", "POST")).toHaveLength(1);
  });

  it("times out stalled polls, reports contact loss, and stops at the cap", async () => {
    runHandler = hangsUntilAbort;
    await mount();
    await openAndPrint();
    for (let i = 0; i < POLL_CAP_MS / (POLL_INTERVAL_MS + READ_TIMEOUT_MS); i++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS + READ_TIMEOUT_MS);
      });
      if (i === 2) expect(screen.getByTestId("print-lost-contact").textContent).toContain("last status: queued");
    }
    expect(screen.getByTestId("print-gave-up")).toBeTruthy();
    const count = calls("/runs/42").length;
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(calls("/runs/42")).toHaveLength(count);
    expect(calls("/print", "POST")).toHaveLength(1);
  });
});

describe("print bridge response deadlines", () => {
  it.each([
    ["printers", () => fetchPrinters(BRIDGE), READ_TIMEOUT_MS, 200],
    ["run", () => fetchRun(BRIDGE, 42), READ_TIMEOUT_MS, 200],
    ["print accepted", () => startPrint(BRIDGE, BD_PRESET, 1, 1), PRINT_TIMEOUT_MS, 202],
    ["print conflict", () => startPrint(BRIDGE, BD_PRESET, 1, 1), PRINT_TIMEOUT_MS, 409],
    ["print error", () => startPrint(BRIDGE, BD_PRESET, 1, 1), PRINT_TIMEOUT_MS, 502],
  ])("bounds a stalled %s response body", async (_label, request, timeout, status) => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(async (url: string, init?: RequestInit) => ({
      ok: status < 400,
      status,
      json: () => hangsUntilAbort(url, init),
    }));
    let settled = false;
    const pending = request().catch((error: Error) => ({ kind: "error", message: error.message }))
      .then((result) => { settled = true; return result; });
    await vi.advanceTimersByTimeAsync(timeout - 1);
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(await pending).toEqual({ kind: "error", message: NETWORK_MESSAGE });
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("BdDetailPage wiring", () => {
  const MODEL: BdDetailPageModel = {
    slug: "holder-spray-can",
    title: "Spray Can Holder",
    blurb: "A holder.",
    params: [],
    presets: [{ id: "spray_can", label: "Spray Can", values: {} }],
  };

  it("renders no Print button without the env var", async () => {
    vi.stubEnv("NEXT_PUBLIC_PRINT_BRIDGE_URL", "");
    render(<BdDetailPage model={MODEL} />);
    await act(async () => {});
    expect(screen.queryByTestId("print-button")).toBeNull();
    expect(screen.getByTestId("bd-download-stl")).toBeTruthy();
  });

  it("prints the baked preset the Download button would fetch", async () => {
    render(<BdDetailPage model={MODEL} />);
    await act(async () => {});
    expect(screen.getAllByTestId("print-button")).toHaveLength(1);
    await openAndPrint();
    expect(postedBody()).toMatchObject({ source: "bd", slug: "holder-spray-can", preset: "spray_can" });
  });
});
