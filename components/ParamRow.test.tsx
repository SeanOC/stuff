// @vitest-environment jsdom

// Guards the "do not clamp on typing" contract. The slider is bounded
// to [min,max] but the numeric input accepts anything — OpenSCAD
// decides what's valid on render, not the form. Clamping on input
// would silently mask "preview 500 mm to see what breaks" workflows.

import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ParamRow } from "./ParamRow";
import type { NumberParam, StringParam } from "@/lib/scad-params/parse";

describe("ParamRow number input", () => {
  it("accepts an out-of-range typed value without clamping", () => {
    const param: NumberParam = {
      kind: "number",
      name: "can_diameter",
      label: "Item diameter",
      unit: "mm",
      default: 70,
      min: 20,
      max: 200,
      step: 0.5,
    };
    const onChange = vi.fn();
    const { getByLabelText } = render(
      <ParamRow param={param} value={70} onChange={onChange} />,
    );

    const input = getByLabelText("Item diameter") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "999" } });

    // The callback sees the unclamped value — OpenSCAD will reject at
    // render time, the form does not second-guess.
    expect(onChange).toHaveBeenCalledWith("can_diameter", 999);
    // The min/max attributes are wired so the browser's native :invalid
    // fires (validation.spec.ts covers the full range check in-browser).
    expect(input.getAttribute("min")).toBe("20");
    expect(input.getAttribute("max")).toBe("200");
  });
});

describe("ParamRow string input (labels L4, pst-egc3j)", () => {
  // Rows share id="param-<name>", so a leftover render would steal the label.
  afterEach(cleanup);
  const param: StringParam = {
    kind: "string",
    name: "text",
    label: "Label text",
    default: "Filament",
    maxLength: 24,
    charset: "printable-ascii",
  };

  it("carries the manifest's maxLength and a printable-ASCII pattern", () => {
    const { getByLabelText } = render(
      <ParamRow param={param} value="PLA" onChange={vi.fn()} />,
    );
    const input = getByLabelText("Label text") as HTMLInputElement;
    expect(input.maxLength).toBe(24);
    const pattern = new RegExp(`^(?:${input.getAttribute("pattern")})$`, "v");
    expect(pattern.test("PETG-CF 1.75 ~!")).toBe(true);
    expect(pattern.test("café")).toBe(false);
  });

  it("reports each edit without rendering, and shows an inline error under the row", () => {
    const onChange = vi.fn();
    const { getByLabelText, getByTestId, rerender, queryByTestId } = render(
      <ParamRow param={param} value="PLA" onChange={onChange} />,
    );
    expect(queryByTestId("param-error-text")).toBeNull();
    fireEvent.change(getByLabelText("Label text"), { target: { value: "PLA+" } });
    expect(onChange).toHaveBeenCalledWith("text", "PLA+");
    rerender(<ParamRow param={param} value="PLA+" onChange={onChange} error="below the 1.2 mm floor" />);
    expect(getByTestId("param-error-text").textContent).toBe("below the 1.2 mm floor");
  });
});
