// @vitest-environment jsdom

// st-yxj: presets moved from the metadata left rail into the param
// rail. ParamRail now optionally renders a `<PresetSection>` at the
// top when preset props are supplied.

import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ParamRail } from "./ParamRail";
import type { Param } from "@/lib/scad-params/parse";

describe("ParamRail preset section", () => {
  const oneParam: Param[] = [
    {
      kind: "number",
      name: "x",
      label: "X",
      default: 1,
      min: 0,
      max: 10,
      step: 0.5,
    },
  ];

  it("does NOT render a preset list when preset props are absent", () => {
    const { queryByTestId } = render(
      <ParamRail
        params={oneParam}
        values={{ x: 1 }}
        onChange={vi.fn()}
      />,
    );
    expect(queryByTestId("preset-list")).toBeNull();
  });

  it("renders the preset list when presets are supplied", () => {
    const { getByTestId, getByText } = render(
      <ParamRail
        params={oneParam}
        values={{ x: 1 }}
        onChange={vi.fn()}
        presets={[{ id: "stock", label: "Stock", isUser: false }]}
        activePresetId="stock"
        modified={false}
        onLoadPreset={vi.fn()}
        onDeletePreset={vi.fn()}
        onSavePreset={vi.fn()}
        saveRowOpen={false}
        setSaveRowOpen={vi.fn()}
      />,
    );
    expect(getByTestId("preset-list")).toBeTruthy();
    expect(getByText("Stock")).toBeTruthy();
  });
});
