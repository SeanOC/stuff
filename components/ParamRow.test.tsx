// @vitest-environment jsdom

// Guards the "do not clamp on typing" contract. The slider is bounded
// to [min,max] but the numeric input accepts anything — OpenSCAD
// decides what's valid on render, not the form. Clamping on input
// would silently mask "preview 500 mm to see what breaks" workflows.

import { fireEvent, render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ParamRow } from "./ParamRow";
import type { NumberParam } from "@/lib/scad-params/parse";

describe("ParamRow number input", () => {
  it("accepts an out-of-range typed value without clamping", () => {
    const param: NumberParam = {
      kind: "number",
      name: "can_diameter",
      shortKey: "d",
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
