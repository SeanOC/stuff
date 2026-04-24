// Share-URL encode/decode. Uses each param's `shortKey` alias from
// the SCAD parser so a live slider state compresses to a terse query
// string — `?d=70&c=0.25` rather than `?can_diameter=70&clearance=0.25`.
//
// Only params whose value differs from their default are emitted so a
// shared link stays short and a reader can see at a glance what the
// sharer actually tweaked. Booleans → `1`/`0` (one byte saved per
// flag vs `true`/`false`).
//
// Decoder is forgiving: unknown keys and type-mismatched values become
// structured warnings the UI can surface, rather than throwing. A
// mangled URL hydrates whatever IS valid and reports the rest.

import type { Param, ParamValue } from "@/lib/scad-params/parse";

export type ShareWarning =
  | { kind: "unknown"; key: string }
  | { kind: "invalid"; name: string; raw: string; reason: string };

export interface DecodeResult {
  values: Partial<Record<string, ParamValue>>;
  warnings: ShareWarning[];
}

export function encodeShare(
  params: readonly Param[],
  values: Record<string, ParamValue>,
): string {
  const q = new URLSearchParams();
  for (const p of params) {
    const v = values[p.name];
    if (v === undefined) continue;
    if (isDefault(p, v)) continue;
    q.set(p.shortKey, encodeValue(p, v));
  }
  return q.toString();
}

export function decodeShare(
  params: readonly Param[],
  query: URLSearchParams,
): DecodeResult {
  const byShort = new Map<string, Param>();
  for (const p of params) byShort.set(p.shortKey, p);

  const values: Partial<Record<string, ParamValue>> = {};
  const warnings: ShareWarning[] = [];
  for (const [key, raw] of query) {
    const param = byShort.get(key);
    if (!param) {
      warnings.push({ kind: "unknown", key });
      continue;
    }
    const parsed = decodeValue(param, raw);
    if (parsed.kind === "invalid") {
      warnings.push({
        kind: "invalid",
        name: param.name,
        raw,
        reason: parsed.reason,
      });
      continue;
    }
    values[param.name] = parsed.value;
  }
  return { values, warnings };
}

function isDefault(param: Param, value: ParamValue): boolean {
  return value === param.default;
}

function encodeValue(param: Param, value: ParamValue): string {
  switch (param.kind) {
    case "boolean":
      return value ? "1" : "0";
    case "number":
    case "integer":
      return String(value);
    case "string":
    case "enum":
      return String(value);
  }
}

type DecodeOk = { kind: "ok"; value: ParamValue };
type DecodeBad = { kind: "invalid"; reason: string };

function decodeValue(param: Param, raw: string): DecodeOk | DecodeBad {
  switch (param.kind) {
    case "boolean": {
      // Accept 1/0 (our encoder) plus true/false (pasted from logs).
      if (raw === "1" || raw.toLowerCase() === "true") {
        return { kind: "ok", value: true };
      }
      if (raw === "0" || raw.toLowerCase() === "false") {
        return { kind: "ok", value: false };
      }
      return { kind: "invalid", reason: "expected 1/0 or true/false" };
    }
    case "number":
    case "integer": {
      const n = Number(raw);
      if (!Number.isFinite(n)) {
        return { kind: "invalid", reason: "not numeric" };
      }
      return {
        kind: "ok",
        value: param.kind === "integer" ? Math.trunc(n) : n,
      };
    }
    case "enum": {
      if (!param.choices.includes(raw)) {
        return {
          kind: "invalid",
          reason: `not in choices [${param.choices.join("|")}]`,
        };
      }
      return { kind: "ok", value: raw };
    }
    case "string":
      return { kind: "ok", value: raw };
  }
}
