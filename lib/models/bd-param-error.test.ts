import { describe, expect, it } from "vitest";
import type { Param } from "@/lib/scad-params/parse";
import { paramErrorsFor } from "./bd-param-error";

const TEXT: Param = { name: "text", kind: "string", default: "Filament", maxLength: 24 };
const SIZE: Param = { name: "size", kind: "enum", default: "a", choices: ["a", "b"] };
const D: Param = { name: "d", kind: "number", default: 66, min: 30, max: 120 };

describe("paramErrorsFor", () => {
  it("attributes a message that names its param (route and service forms)", () => {
    expect(paramErrorsFor([TEXT, SIZE], "size: x not in a|b")).toEqual({ size: "size: x not in a|b" });
    expect(paramErrorsFor([D], "param d: 999 above max 120")).toEqual({ d: "param d: 999 above max 120" });
  });

  it("puts an unnamed build-time rejection under the model's only text param", () => {
    const floor = "label text 'WWW' is too long for a 60 x 14 mm card: below the 1.2 mm floor";
    expect(paramErrorsFor([TEXT, SIZE], floor)).toEqual({ text: floor });
  });

  it("leaves an unattributable message to the viewer banner", () => {
    expect(paramErrorsFor([D, SIZE], "something odd")).toEqual({});
    expect(paramErrorsFor([TEXT, { ...TEXT, name: "sub" }], "something odd")).toEqual({});
  });
});
