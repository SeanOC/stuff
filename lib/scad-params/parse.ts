// Inline-annotation parser for OpenSCAD parameter blocks.
//
// Convention:
//   // === User-tunable parameters ===
//   can_diameter = 46;     // @param number min=20 max=200 step=1 unit=mm group=geometry label="Can diameter"
//   front_open  = true;    // @param boolean label="Open front?"
//   variant     = "round"; // @param enum choices=round|square|hex
//   ...
//   // === Anything else ===     <-- parser stops here
//
// `unit=` and `group=` are optional free-form annotations. `unit` is a
// display-only string shown next to the control (e.g. "mm", "deg", "ms").
// `group=` is a slug used to bucket params in the UI — first-occurrence
// order is the display order of groups.
//
// Pure function, no fs/io. Every public type is exported so the form
// builder and the WASM driver can share param shapes.

export type ParamType = "number" | "integer" | "boolean" | "string" | "enum";

export interface ParamBase {
  name: string;
  label?: string;
  group?: string;
  unit?: string;
}

export interface NumberParam extends ParamBase {
  kind: "number" | "integer";
  default: number;
  min?: number;
  max?: number;
  step?: number;
}

export interface BooleanParam extends ParamBase {
  kind: "boolean";
  default: boolean;
}

export interface StringParam extends ParamBase {
  kind: "string";
  default: string;
}

export interface EnumParam extends ParamBase {
  kind: "enum";
  default: string;
  choices: string[];
}

export type Param = NumberParam | BooleanParam | StringParam | EnumParam;

export interface ParseResult {
  params: Param[];
  warnings: string[];
}

const SECTION_RE = /^\s*\/\/\s*={2,}\s*(.*?)\s*={2,}\s*$/;
const USER_TUNABLE_RE = /user[-_ ]tunable/i;
// Capture: name, default-expression, trailing comment
const PARAM_LINE_RE =
  /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);\s*\/\/\s*(.*)$/;
const ANNOTATION_RE = /^@param\s+(\w+)\b\s*(.*)$/;

export function parseScadParams(source: string): ParseResult {
  const lines = source.split(/\r?\n/);
  const params: Param[] = [];
  const warnings: string[] = [];

  let inBlock = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const section = line.match(SECTION_RE);
    if (section) {
      // A `// === ... ===` line either starts the user-tunable block
      // or terminates it (any subsequent === ends the section).
      if (!inBlock && USER_TUNABLE_RE.test(section[1])) {
        inBlock = true;
      } else if (inBlock) {
        break;
      }
      continue;
    }
    if (!inBlock) continue;

    const m = line.match(PARAM_LINE_RE);
    if (!m) continue;
    const [, name, rawDefault, comment] = m;
    const ann = comment.trim().match(ANNOTATION_RE);
    if (!ann) continue; // line has a comment but no @param — silently skip

    const [, typeKw, attrText] = ann;
    const attrs = parseAttrs(attrText);
    const param = buildParam({
      name,
      typeKw,
      rawDefault: rawDefault.trim(),
      attrs,
      lineNo: i + 1,
      warnings,
    });
    if (param) params.push(param);
  }

  return { params, warnings };
}

// ---- internal helpers --------------------------------------------------

function buildParam(args: {
  name: string;
  typeKw: string;
  rawDefault: string;
  attrs: Map<string, string>;
  lineNo: number;
  warnings: string[];
}): Param | null {
  const { name, typeKw, rawDefault, attrs, lineNo, warnings } = args;
  const base = pickBaseAttrs(name, attrs);
  switch (typeKw) {
    case "number":
    case "integer": {
      const def = Number(rawDefault);
      if (!Number.isFinite(def)) {
        warnings.push(`line ${lineNo}: ${name} default is not numeric`);
        return null;
      }
      const out: NumberParam = {
        ...base,
        kind: typeKw,
        default: typeKw === "integer" ? Math.trunc(def) : def,
      };
      if (attrs.has("min")) out.min = Number(attrs.get("min"));
      if (attrs.has("max")) out.max = Number(attrs.get("max"));
      if (attrs.has("step")) out.step = Number(attrs.get("step"));
      return out;
    }
    case "boolean": {
      const lower = rawDefault.toLowerCase();
      if (lower !== "true" && lower !== "false") {
        warnings.push(`line ${lineNo}: ${name} boolean default must be true/false`);
        return null;
      }
      return { ...base, kind: "boolean", default: lower === "true" };
    }
    case "string": {
      const unquoted = unquote(rawDefault);
      return { ...base, kind: "string", default: unquoted };
    }
    case "enum": {
      const choicesRaw = attrs.get("choices");
      if (!choicesRaw) {
        warnings.push(`line ${lineNo}: ${name} enum missing choices=`);
        return null;
      }
      const choices = choicesRaw.split("|").map((s) => s.trim()).filter(Boolean);
      if (choices.length === 0) {
        warnings.push(`line ${lineNo}: ${name} enum has empty choices`);
        return null;
      }
      const def = unquote(rawDefault);
      if (!choices.includes(def)) {
        warnings.push(
          `line ${lineNo}: ${name} default ${JSON.stringify(def)} not in choices [${choices.join(",")}]`,
        );
      }
      return { ...base, kind: "enum", default: def, choices };
    }
    default:
      warnings.push(`line ${lineNo}: ${name} unknown @param type ${typeKw}`);
      return null;
  }
}

// Extract common ParamBase fields (name + optional label/group/unit) from
// the attribute map. Builds the object with only set keys so `toEqual`
// comparisons against sparse test fixtures keep working.
function pickBaseAttrs(name: string, attrs: Map<string, string>): ParamBase {
  const out: ParamBase = { name };
  const label = attrs.get("label");
  const group = attrs.get("group");
  const unit = attrs.get("unit");
  if (label) out.label = label;
  if (group) out.group = group;
  if (unit) out.unit = unit;
  return out;
}

// Parse `min=20 max=200 step=1 label="Can diameter" choices=a|b|c`. Quoted
// values may contain spaces; bare values may not.
function parseAttrs(text: string): Map<string, string> {
  const attrs = new Map<string, string>();
  const re = /(\w+)=("(?:[^"\\]|\\.)*"|\S+)/g;
  for (const m of text.matchAll(re)) {
    const [, key, value] = m;
    attrs.set(key, unquote(value));
  }
  return attrs;
}

function unquote(s: string): string {
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    return s.slice(1, -1).replace(/\\(.)/g, "$1");
  }
  return s;
}

// ---- runtime helpers exported for the form ----------------------------

export type ParamValue = number | boolean | string;

/** Build a `name=value` dict of defaults for initializing form state. */
export function defaultsOf(params: Param[]): Record<string, ParamValue> {
  const out: Record<string, ParamValue> = {};
  for (const p of params) out[p.name] = p.default;
  return out;
}

/** Format current values as OpenSCAD `-D name=value` flags. */
export function formatDFlags(
  params: Param[],
  values: Record<string, ParamValue>,
): string[] {
  return params.map((p) => {
    const v = values[p.name] ?? p.default;
    return `-D ${p.name}=${formatScadLiteral(p, v)}`;
  });
}

/**
 * Replace each parsed param's top-level assignment in `source` with the
 * caller's value. Required because openscad-wasm-prebuilt silently
 * ignores command-line `-D` flags — we cannot override at the CLI, so
 * we mutate the source instead.
 *
 * Only the first occurrence of `<name> = ...;` (anchored to the start
 * of a line) is replaced, which is the @param's own declaration line.
 * Later assignments (e.g. inside a module body) are untouched.
 */
export function applyParamOverrides(
  source: string,
  params: Param[],
  values: Record<string, ParamValue>,
): string {
  let out = source;
  for (const p of params) {
    const v = values[p.name] ?? p.default;
    const re = new RegExp(
      `^([ \\t]*)${escapeRegex(p.name)}([ \\t]*=)[^;]+;`,
      "m",
    );
    out = out.replace(re, `$1${p.name}$2 ${formatScadLiteral(p, v)};`);
  }
  return out;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Render a SCAD-source-safe literal for one param value. */
export function formatScadLiteral(param: Param, value: ParamValue): string {
  switch (param.kind) {
    case "boolean":
      return value ? "true" : "false";
    case "number":
    case "integer":
      return String(value);
    case "string":
    case "enum":
      return `"${String(value).replace(/(["\\])/g, "\\$1")}"`;
  }
}
