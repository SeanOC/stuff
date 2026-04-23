import { describe, expect, it } from "vitest";
import {
  applyParamOverrides,
  defaultsOf,
  formatDFlags,
  formatScadLiteral,
  parseScadParams,
  type EnumParam,
  type NumberParam,
  type Param,
} from "./parse";

const HEADER = "// === User-tunable parameters ===\n";
const FOOTER = "\n// === End ===\n  cube([10,10,10]);\n";

function wrap(body: string): string {
  return HEADER + body + FOOTER;
}

describe("parseScadParams", () => {
  it("returns empty when no user-tunable section is present", () => {
    const out = parseScadParams("cube([1,2,3]);");
    expect(out.params).toEqual([]);
    expect(out.warnings).toEqual([]);
  });

  it("parses a number with min/max/step/label", () => {
    const out = parseScadParams(
      wrap('can_d = 46;     // @param number min=20 max=200 step=1 label="Can diameter"'),
    );
    expect(out.params).toEqual([
      {
        kind: "number",
        name: "can_d",
        default: 46,
        min: 20,
        max: 200,
        step: 1,
        label: "Can diameter",
      },
    ]);
    expect(out.warnings).toEqual([]);
  });

  it("parses a number without any attributes", () => {
    const out = parseScadParams(wrap("wall = 3; // @param number"));
    expect(out.params).toHaveLength(1);
    const p = out.params[0] as NumberParam;
    expect(p.kind).toBe("number");
    expect(p.default).toBe(3);
    expect(p.min).toBeUndefined();
    expect(p.max).toBeUndefined();
  });

  it("integer truncates a float default", () => {
    const out = parseScadParams(wrap("count = 4.7; // @param integer"));
    expect((out.params[0] as NumberParam).default).toBe(4);
    expect(out.params[0].kind).toBe("integer");
  });

  it("parses booleans true and false", () => {
    const out = parseScadParams(
      wrap("a = true;  // @param boolean\nb = false; // @param boolean label=\"Open?\""),
    );
    expect(out.params).toEqual([
      { kind: "boolean", name: "a", default: true },
      { kind: "boolean", name: "b", default: false, label: "Open?" },
    ]);
  });

  it("rejects non-true/false boolean default with a warning", () => {
    const out = parseScadParams(wrap("a = 1; // @param boolean"));
    expect(out.params).toEqual([]);
    expect(out.warnings[0]).toMatch(/boolean default/);
  });

  it("parses an enum with choices and validates default", () => {
    const out = parseScadParams(
      wrap('shape = "round"; // @param enum choices=round|square|hex label="Shape"'),
    );
    const p = out.params[0] as EnumParam;
    expect(p.kind).toBe("enum");
    expect(p.choices).toEqual(["round", "square", "hex"]);
    expect(p.default).toBe("round");
    expect(p.label).toBe("Shape");
    expect(out.warnings).toEqual([]);
  });

  it("warns when enum default is not among choices", () => {
    const out = parseScadParams(
      wrap('shape = "oval"; // @param enum choices=round|square'),
    );
    expect(out.params).toHaveLength(1);
    expect(out.warnings[0]).toMatch(/not in choices/);
  });

  it("warns when enum has no choices", () => {
    const out = parseScadParams(wrap('s = "x"; // @param enum'));
    expect(out.params).toEqual([]);
    expect(out.warnings[0]).toMatch(/missing choices/);
  });

  it("parses a string with default", () => {
    const out = parseScadParams(wrap('label = "hello world"; // @param string'));
    expect(out.params).toEqual([
      { kind: "string", name: "label", default: "hello world" },
    ]);
  });

  it("stops at the next === section header", () => {
    const src =
      "// === User-tunable parameters ===\n" +
      "a = 1; // @param number\n" +
      "// === Internals ===\n" +
      "b = 2; // @param number\n";
    const out = parseScadParams(src);
    expect(out.params.map((p) => p.name)).toEqual(["a"]);
  });

  it("ignores plain comments and assignments without @param", () => {
    const out = parseScadParams(
      wrap(
        "// just a comment\n" +
          "a = 1; // not annotated\n" +
          "b = 2; // @param number",
      ),
    );
    expect(out.params.map((p) => p.name)).toEqual(["b"]);
  });

  it("parses unit= only", () => {
    const out = parseScadParams(wrap("w = 3; // @param number unit=mm"));
    expect(out.params).toHaveLength(1);
    expect(out.params[0].unit).toBe("mm");
    expect(out.params[0].group).toBeUndefined();
  });

  it("parses group= only", () => {
    const out = parseScadParams(wrap("rows = 2; // @param integer group=layout"));
    expect(out.params).toHaveLength(1);
    expect(out.params[0].group).toBe("layout");
    expect(out.params[0].unit).toBeUndefined();
  });

  it("leaves unit and group undefined when both absent", () => {
    const out = parseScadParams(wrap("a = 1; // @param number"));
    expect(out.params).toHaveLength(1);
    expect(out.params[0].unit).toBeUndefined();
    expect(out.params[0].group).toBeUndefined();
  });

  it("parses unit= and group= together on any @param kind", () => {
    const out = parseScadParams(
      wrap(
        'can_d = 46;  // @param number min=20 max=200 unit=mm group=cans label="Can diameter"\n' +
          'drain  = "slots"; // @param enum choices=slots|holes|open unit="" group=drainage\n' +
          'open   = true; // @param boolean group=cans',
      ),
    );
    expect(out.params).toHaveLength(3);
    expect(out.params[0]).toMatchObject({
      name: "can_d",
      kind: "number",
      unit: "mm",
      group: "cans",
      label: "Can diameter",
    });
    expect(out.params[1]).toMatchObject({
      name: "drain",
      kind: "enum",
      group: "drainage",
    });
    expect(out.params[2]).toMatchObject({
      name: "open",
      kind: "boolean",
      group: "cans",
    });
  });

  it("survives the real cylindrical_holder_slot header pattern", () => {
    // Mirrors the actual file's section delimiter style.
    const src = `
include <BOSL2/std.scad>

// === User-tunable parameters ===
can_diameter = 46;     // @param number min=20 max=200 step=0.5 label="Can diameter (mm)"
clearance    = 0.25;   // @param number min=0 max=1 step=0.05 label="Slip clearance"
front_open   = true;   // @param boolean label="Front opening?"
slot_count   = 2;      // @param integer min=1 max=6 label="Slot count"

module foo() {}
`;
    const out = parseScadParams(src);
    expect(out.params.map((p) => p.name)).toEqual([
      "can_diameter",
      "clearance",
      "front_open",
      "slot_count",
    ]);
    expect(out.warnings).toEqual([]);
  });
});

describe("defaultsOf / formatScadLiteral / formatDFlags", () => {
  const params = parseScadParams(
    wrap(
      "n = 1.5; // @param number\n" +
        "k = 2;   // @param integer\n" +
        'b = false; // @param boolean\n' +
        's = "hi"; // @param string\n' +
        'e = "x"; // @param enum choices=x|y|z',
    ),
  ).params;

  it("defaultsOf returns name->default", () => {
    expect(defaultsOf(params)).toEqual({
      n: 1.5,
      k: 2,
      b: false,
      s: "hi",
      e: "x",
    });
  });

  it("formatScadLiteral quotes strings/enums and unquotes booleans/numbers", () => {
    expect(formatScadLiteral(params[0], 1.5)).toBe("1.5");
    expect(formatScadLiteral(params[2], true)).toBe("true");
    expect(formatScadLiteral(params[3], 'a"b')).toBe('"a\\"b"');
    expect(formatScadLiteral(params[4], "y")).toBe('"y"');
  });

  it("formatDFlags emits one -D per param", () => {
    const flags = formatDFlags(params, defaultsOf(params));
    expect(flags).toEqual([
      "-D n=1.5",
      "-D k=2",
      "-D b=false",
      '-D s="hi"',
      '-D e="x"',
    ]);
  });
});

describe("applyParamOverrides", () => {
  const params: Param[] = [
    { kind: "number", name: "can_diameter", default: 46 },
    { kind: "boolean", name: "use_cup", default: true },
    { kind: "enum", name: "variant", default: "round", choices: ["round", "square"] },
  ];

  it("rewrites the @param's own assignment line", () => {
    const src = [
      "// === User-tunable parameters ===",
      "can_diameter = 46;     // @param number",
      "use_cup      = true;   // @param boolean",
      "variant      = \"round\"; // @param enum choices=round|square",
      "// === Derived ===",
      "ring_id = can_diameter + 1;",
    ].join("\n");
    const out = applyParamOverrides(src, params, {
      can_diameter: 80,
      use_cup: false,
      variant: "square",
    });
    // Aligned whitespace around `=` is preserved so the file stays
    // visually consistent if anyone inspects it later.
    expect(out).toContain("can_diameter = 80;");
    expect(out).toContain("use_cup      = false;");
    expect(out).toContain('variant      = "square";');
    // Derived expressions are untouched (still reference the variable).
    expect(out).toContain("ring_id = can_diameter + 1;");
  });

  it("falls back to defaults for missing keys", () => {
    const src = "can_diameter = 46;     // @param number\n";
    const out = applyParamOverrides(src, params.slice(0, 1), {});
    expect(out).toContain("can_diameter = 46;");
  });

  it("only replaces the first (top-level) assignment, not later mentions", () => {
    const src = [
      "can_diameter = 46;     // @param number",
      "module foo() { can_diameter = 999; cube(can_diameter); }",
    ].join("\n");
    const out = applyParamOverrides(src, [params[0]], { can_diameter: 80 });
    expect(out).toContain("can_diameter = 80;");
    // The module-local reassignment is left alone.
    expect(out).toContain("can_diameter = 999;");
  });

  it("escapes regex-meaningful characters in param names", () => {
    // OpenSCAD allows underscores; just confirms we don't crash on
    // realistic names that look benign but pass through escapeRegex.
    const p: Param[] = [{ kind: "number", name: "a_b_c", default: 1 }];
    const out = applyParamOverrides("a_b_c = 1;", p, { a_b_c: 9 });
    expect(out).toBe("a_b_c = 9;");
  });
});
