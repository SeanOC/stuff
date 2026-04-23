"use client";

// One row of the grouped param rail. Dispatches on param.kind to a
// per-kind sub-component so the shared row chrome (label, unit, id
// scoping) stays in one place and each input type only carries its own
// controls.
//
// Typing an out-of-range value into a number input is allowed: the
// browser marks the input :invalid (the native HTML5 validity flag),
// but we do not clamp or reject on change — OpenSCAD will reject on
// render and surface a parser error. Clamping on input would prevent
// "preview 220 mm to see what breaks" workflows the CAD-y users expect.

import clsx from "clsx";
import type {
  BooleanParam,
  EnumParam,
  NumberParam,
  Param,
  ParamValue,
  StringParam,
} from "@/lib/scad-params/parse";

interface Props {
  param: Param;
  value: ParamValue | undefined;
  onChange: (name: string, value: ParamValue) => void;
}

export function ParamRow({ param, value, onChange }: Props) {
  switch (param.kind) {
    case "number":
    case "integer":
      return (
        <NumberRow param={param} value={value as number | undefined} onChange={onChange} />
      );
    case "boolean":
      return (
        <BooleanRow param={param} value={value as boolean | undefined} onChange={onChange} />
      );
    case "enum":
      return (
        <EnumRow param={param} value={value as string | undefined} onChange={onChange} />
      );
    case "string":
      return (
        <StringRow param={param} value={value as string | undefined} onChange={onChange} />
      );
    default:
      return exhaustive(param);
  }
}

function NumberRow({
  param,
  value,
  onChange,
}: {
  param: NumberParam;
  value: number | undefined;
  onChange: (name: string, value: ParamValue) => void;
}) {
  const v = value ?? param.default;
  const isInt = param.kind === "integer";
  const step = param.step ?? (isInt ? 1 : 0.1);
  const showSlider = param.min !== undefined && param.max !== undefined;
  const id = `param-${param.name}`;
  const label = param.label ?? param.name;
  // Flat 3-col grid so #param-<name>'s direct parent also holds the
  // slider. model-page.spec.ts walks xpath=.. then expects an
  // input[type=range] sibling — a nested wrapper around the number
  // input would hide the slider from that probe.
  return (
    <div className="grid grid-cols-[1fr_auto_auto] items-baseline gap-x-8 gap-y-3">
      <label htmlFor={id} className="text-11 text-text">
        {label}
      </label>
      <input
        id={id}
        type="number"
        min={param.min}
        max={param.max}
        step={step}
        value={v}
        onChange={(e) => onChange(param.name, parseNum(e.target.value, isInt))}
        className={clsx(
          "w-64 rounded-3 border border-line bg-panel2 px-4 py-2",
          "font-mono text-11 text-text",
          "invalid:border-red",
          "focus:border-accent-line focus:outline-none",
        )}
      />
      <span className="font-mono text-10 text-text-mute">
        {param.unit ?? ""}
      </span>
      {showSlider && (
        <input
          type="range"
          min={param.min}
          max={param.max}
          step={step}
          value={Math.min(Math.max(v, param.min!), param.max!)}
          onChange={(e) => onChange(param.name, parseNum(e.target.value, isInt))}
          aria-label={`${label} slider`}
          className="col-span-3 h-4 w-full"
        />
      )}
      {showSlider && (
        <div className="col-span-3 flex justify-between font-mono text-10 text-text-mute">
          <span>{param.min}</span>
          <span>{param.max}</span>
        </div>
      )}
    </div>
  );
}

function BooleanRow({
  param,
  value,
  onChange,
}: {
  param: BooleanParam;
  value: boolean | undefined;
  onChange: (name: string, value: ParamValue) => void;
}) {
  const v = value ?? param.default;
  const id = `param-${param.name}`;
  const label = param.label ?? param.name;
  return (
    <div className="flex items-center justify-between gap-8">
      <label htmlFor={id} className="text-11 text-text">
        {label}
      </label>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={v}
        onClick={() => onChange(param.name, !v)}
        className={clsx(
          "relative inline-flex h-14 w-28 items-center rounded-full border transition-colors",
          v ? "border-accent-line bg-accent" : "border-line bg-panel2",
        )}
      >
        <span
          className={clsx(
            "absolute top-2 h-10 w-10 rounded-full transition-all",
            v ? "left-16 bg-accent-ink" : "left-2 bg-text-mute",
          )}
        />
      </button>
    </div>
  );
}

function EnumRow({
  param,
  value,
  onChange,
}: {
  param: EnumParam;
  value: string | undefined;
  onChange: (name: string, value: ParamValue) => void;
}) {
  const v = value ?? param.default;
  const id = `param-${param.name}`;
  const label = param.label ?? param.name;
  return (
    <div className="flex items-center justify-between gap-8">
      <label htmlFor={id} className="text-11 text-text">
        {label}
      </label>
      <select
        id={id}
        value={v}
        onChange={(e) => onChange(param.name, e.target.value)}
        className={clsx(
          "rounded-3 border border-line bg-panel2 px-4 py-2",
          "font-mono text-11 text-text",
          "focus:border-accent-line focus:outline-none",
        )}
      >
        {param.choices.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
    </div>
  );
}

function StringRow({
  param,
  value,
  onChange,
}: {
  param: StringParam;
  value: string | undefined;
  onChange: (name: string, value: ParamValue) => void;
}) {
  const v = value ?? param.default;
  const id = `param-${param.name}`;
  const label = param.label ?? param.name;
  return (
    <div className="flex items-center justify-between gap-8">
      <label htmlFor={id} className="text-11 text-text">
        {label}
      </label>
      <input
        id={id}
        type="text"
        value={v}
        onChange={(e) => onChange(param.name, e.target.value)}
        className={clsx(
          "flex-1 rounded-3 border border-line bg-panel2 px-4 py-2",
          "font-mono text-11 text-text",
          "focus:border-accent-line focus:outline-none",
        )}
      />
    </div>
  );
}

function parseNum(raw: string, asInt: boolean): number {
  const n = asInt ? parseInt(raw, 10) : parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

function exhaustive(x: never): never {
  throw new Error(`unreachable param kind: ${JSON.stringify(x)}`);
}
