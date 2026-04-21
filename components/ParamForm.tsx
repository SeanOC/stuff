"use client";

// Auto-generates one form control per parsed @param. Number → range
// slider + numeric input pair. Boolean → checkbox. Enum → select.
// String → text input.

import type { Param, ParamValue } from "@/lib/scad-params/parse";

interface Props {
  params: Param[];
  values: Record<string, ParamValue>;
  onChange: (next: Record<string, ParamValue>) => void;
}

export default function ParamForm({ params, values, onChange }: Props) {
  if (params.length === 0) {
    return <p style={{ color: "#8b949e" }}>No parameters in this model.</p>;
  }

  function update(name: string, value: ParamValue) {
    onChange({ ...values, [name]: value });
  }

  return (
    <form style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
      {params.map((p) => (
        <ParamRow key={p.name} param={p} value={values[p.name]} onChange={(v) => update(p.name, v)} />
      ))}
    </form>
  );
}

function ParamRow({
  param,
  value,
  onChange,
}: {
  param: Param;
  value: ParamValue | undefined;
  onChange: (v: ParamValue) => void;
}) {
  const label = param.label ?? param.name;
  const id = `param-${param.name}`;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
      <label htmlFor={id} style={{ fontSize: "0.85rem", color: "#c9d1d9" }}>
        {label}
        <span style={{ color: "#6e7681", fontFamily: "ui-monospace, monospace", marginLeft: "0.5rem", fontSize: "0.75rem" }}>
          {param.name}
        </span>
      </label>
      <ParamControl id={id} param={param} value={value} onChange={onChange} />
    </div>
  );
}

function ParamControl({
  id,
  param,
  value,
  onChange,
}: {
  id: string;
  param: Param;
  value: ParamValue | undefined;
  onChange: (v: ParamValue) => void;
}) {
  switch (param.kind) {
    case "number":
    case "integer": {
      const v = (value as number | undefined) ?? param.default;
      const isInt = param.kind === "integer";
      const step = param.step ?? (isInt ? 1 : 0.1);
      const showSlider = param.min !== undefined && param.max !== undefined;
      return (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          {showSlider && (
            <input
              type="range"
              min={param.min}
              max={param.max}
              step={step}
              value={v}
              onChange={(e) => onChange(parseNum(e.target.value, isInt))}
              style={{ flex: 1 }}
            />
          )}
          <input
            id={id}
            type="number"
            min={param.min}
            max={param.max}
            step={step}
            value={v}
            onChange={(e) => onChange(parseNum(e.target.value, isInt))}
            style={{ ...inputStyle, width: showSlider ? 80 : "100%" }}
          />
        </div>
      );
    }
    case "boolean": {
      const v = (value as boolean | undefined) ?? param.default;
      return (
        <input
          id={id}
          type="checkbox"
          checked={v}
          onChange={(e) => onChange(e.target.checked)}
          style={{ alignSelf: "flex-start" }}
        />
      );
    }
    case "enum": {
      const v = (value as string | undefined) ?? param.default;
      return (
        <select
          id={id}
          value={v}
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
        >
          {param.choices.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      );
    }
    case "string": {
      const v = (value as string | undefined) ?? param.default;
      return (
        <input
          id={id}
          type="text"
          value={v}
          onChange={(e) => onChange(e.target.value)}
          style={inputStyle}
        />
      );
    }
  }
}

function parseNum(raw: string, asInt: boolean): number {
  const n = asInt ? parseInt(raw, 10) : parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

const inputStyle: React.CSSProperties = {
  background: "#0d1117",
  color: "#e6edf3",
  border: "1px solid #30363d",
  borderRadius: 4,
  padding: "0.3rem 0.5rem",
  fontFamily: "inherit",
};
