import { describe, expect, it } from "vitest";
import { parseRenderError } from "./render-error";

describe("parseRenderError", () => {
  it("parses a parser error with line number", () => {
    const stderr = `WARNING: Ignoring unknown module 'something'
ERROR: Parser error in file "input.scad", line 42: syntax error`;
    expect(parseRenderError(stderr)).toEqual({
      line: 42,
      message: 'Parser error in file "input.scad", line 42: syntax error',
    });
  });

  it("parses an ignored-function error with line number", () => {
    const stderr =
      "ERROR: Ignoring unknown function 'missing()', in file input.scad, line 17";
    expect(parseRenderError(stderr)).toEqual({
      line: 17,
      message:
        "Ignoring unknown function 'missing()', in file input.scad, line 17",
    });
  });

  it("returns line=null when no line number is present", () => {
    const stderr = "ERROR: Unterminated multi-line comment";
    expect(parseRenderError(stderr)).toEqual({
      line: null,
      message: "Unterminated multi-line comment",
    });
  });

  it("skips WARNINGs that precede the first ERROR", () => {
    const stderr = `WARNING: foo, in file a.scad, line 3
WARNING: bar, in file a.scad, line 5
ERROR: Evaluation failed, in file a.scad, line 7`;
    expect(parseRenderError(stderr)).toEqual({
      line: 7,
      message: "Evaluation failed, in file a.scad, line 7",
    });
  });

  it("returns null on empty stderr", () => {
    expect(parseRenderError("")).toBeNull();
  });

  it("returns null when stderr has no ERROR: lines", () => {
    const stderr = "WARNING: something minor\nINFO: manifold backend ready";
    expect(parseRenderError(stderr)).toBeNull();
  });
});
