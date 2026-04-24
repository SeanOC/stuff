import { describe, expect, it } from "vitest";
import { decodeShare, encodeShare } from "./encode";
import type { Param } from "@/lib/scad-params/parse";

const PARAMS: Param[] = [
  { kind: "number", name: "can_diameter", shortKey: "d", default: 70 },
  { kind: "number", name: "clearance", shortKey: "c", default: 0.5 },
  { kind: "integer", name: "rows", shortKey: "r", default: 2 },
  { kind: "boolean", name: "open", shortKey: "o", default: true },
  {
    kind: "enum",
    name: "shape",
    shortKey: "s",
    default: "round",
    choices: ["round", "square", "hex"],
  },
];

describe("encodeShare", () => {
  it("omits params that equal their defaults", () => {
    const q = encodeShare(PARAMS, {
      can_diameter: 70,
      clearance: 0.5,
      rows: 2,
      open: true,
      shape: "round",
    });
    expect(q).toBe("");
  });

  it("emits only the tweaked params keyed by shortKey", () => {
    const q = encodeShare(PARAMS, {
      can_diameter: 46,
      clearance: 0.25,
      rows: 2,
      open: true,
      shape: "round",
    });
    const decoded = new URLSearchParams(q);
    expect(decoded.get("d")).toBe("46");
    expect(decoded.get("c")).toBe("0.25");
    expect([...decoded.keys()].sort()).toEqual(["c", "d"]);
  });

  it("encodes booleans as 1/0", () => {
    const q = new URLSearchParams(
      encodeShare(PARAMS, {
        can_diameter: 70,
        clearance: 0.5,
        rows: 2,
        open: false,
        shape: "round",
      }),
    );
    expect(q.get("o")).toBe("0");
  });

  it("encodes enums as the literal choice string", () => {
    const q = new URLSearchParams(
      encodeShare(PARAMS, {
        can_diameter: 70,
        clearance: 0.5,
        rows: 2,
        open: true,
        shape: "hex",
      }),
    );
    expect(q.get("s")).toBe("hex");
  });
});

describe("decodeShare", () => {
  it("hydrates values by shortKey", () => {
    const { values, warnings } = decodeShare(
      PARAMS,
      new URLSearchParams("d=46&c=0.25&o=0"),
    );
    expect(warnings).toEqual([]);
    expect(values).toEqual({
      can_diameter: 46,
      clearance: 0.25,
      open: false,
    });
  });

  it("warns on unknown query keys but keeps hydrating known ones", () => {
    const { values, warnings } = decodeShare(
      PARAMS,
      new URLSearchParams("d=46&xyz=1"),
    );
    expect(values).toEqual({ can_diameter: 46 });
    expect(warnings).toEqual([{ kind: "unknown", key: "xyz" }]);
  });

  it("warns on a non-numeric number value", () => {
    const { values, warnings } = decodeShare(
      PARAMS,
      new URLSearchParams("d=banana"),
    );
    expect(values).toEqual({});
    expect(warnings).toEqual([
      {
        kind: "invalid",
        name: "can_diameter",
        raw: "banana",
        reason: "not numeric",
      },
    ]);
  });

  it("warns on an enum value outside choices", () => {
    const { warnings } = decodeShare(
      PARAMS,
      new URLSearchParams("s=oval"),
    );
    expect(warnings).toHaveLength(1);
    expect(warnings[0]).toMatchObject({
      kind: "invalid",
      name: "shape",
      reason: "not in choices [round|square|hex]",
    });
  });

  it("accepts true/false in addition to 1/0 for booleans", () => {
    const { values, warnings } = decodeShare(
      PARAMS,
      new URLSearchParams("o=false"),
    );
    expect(values).toEqual({ open: false });
    expect(warnings).toEqual([]);
  });

  it("truncates floats when hydrating integer params", () => {
    const { values } = decodeShare(PARAMS, new URLSearchParams("r=4.7"));
    expect(values).toEqual({ rows: 4 });
  });
});

describe("round-trip", () => {
  it("encode → decode returns the same tweaked values", () => {
    const original = {
      can_diameter: 42,
      clearance: 0.25,
      rows: 3,
      open: false,
      shape: "square" as const,
    };
    const q = encodeShare(PARAMS, original);
    const { values, warnings } = decodeShare(PARAMS, new URLSearchParams(q));
    expect(warnings).toEqual([]);
    // Default-valued entries are omitted from the query, so they
    // don't reappear on decode — that's the contract.
    expect(values).toEqual({
      can_diameter: 42,
      clearance: 0.25,
      rows: 3,
      open: false,
      shape: "square",
    });
  });
});
