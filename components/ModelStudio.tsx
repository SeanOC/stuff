"use client";

// Client-side coordinator: holds form state, debounces it, calls the
// WASM render driver, and shows the resulting STL in a 3D viewer plus
// a -D-flag debug panel (per bead requirement).

import { useEffect, useMemo, useRef, useState } from "react";
import {
  defaultsOf,
  formatDFlags,
  formatScadLiteral,
  type Param,
  type ParamValue,
} from "@/lib/scad-params/parse";
import { renderToStl, type RenderResult } from "@/lib/wasm/render";
import ParamForm from "./ParamForm";
import StlViewer from "./StlViewer";

interface Props {
  modelPath: string;
  source: string;
  params: Param[];
}

const RENDER_DEBOUNCE_MS = 250;

export default function ModelStudio({ modelPath, source, params }: Props) {
  const [values, setValues] = useState<Record<string, ParamValue>>(() =>
    defaultsOf(params),
  );
  const [debouncedValues, setDebouncedValues] = useState(values);
  const [showDebug, setShowDebug] = useState(false);
  const [renderState, setRenderState] = useState<RenderState>({ kind: "idle" });
  const renderToken = useRef(0);

  // Debounce values → debouncedValues (250ms) — bead spec.
  useEffect(() => {
    const id = setTimeout(() => setDebouncedValues(values), RENDER_DEBOUNCE_MS);
    return () => clearTimeout(id);
  }, [values]);

  const dFlags = useMemo(
    () => formatDFlags(params, debouncedValues),
    [params, debouncedValues],
  );

  // Build the SCAD source actually shipped to WASM: original source +
  // overrides at the top so user values win over the file defaults
  // without us having to mutate the original file content.
  const scadWithOverrides = useMemo(() => {
    const overrides = params
      .map((p) => `${p.name} = ${formatScadLiteral(p, debouncedValues[p.name] ?? p.default)};`)
      .join("\n");
    return `${overrides}\n${source}`;
  }, [params, debouncedValues, source]);

  // Trigger a render on every debounced-values change. Use a token so
  // out-of-order completions don't clobber a newer in-flight render.
  useEffect(() => {
    const myToken = ++renderToken.current;
    setRenderState({ kind: "rendering", since: performance.now() });
    void renderToStl({
      source: scadWithOverrides,
      fetchLibFile: fetchLibFromApi,
    }).then((result) => {
      if (myToken !== renderToken.current) return; // stale
      setRenderState(
        result.ok && result.stl
          ? { kind: "ok", result, stl: result.stl }
          : { kind: "error", result },
      );
    });
  }, [scadWithOverrides]);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "1.5rem", marginTop: "1rem" }}>
      <aside>
        <ParamForm params={params} values={values} onChange={setValues} />
        <button
          onClick={() => setShowDebug((s) => !s)}
          style={{
            marginTop: "1rem",
            padding: "0.4rem 0.6rem",
            background: "#21262d",
            color: "#e6edf3",
            border: "1px solid #30363d",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          {showDebug ? "Hide" : "Show"} -D flags
        </button>
        {showDebug && (
          <pre
            style={{
              marginTop: "0.5rem",
              background: "#161b22",
              padding: "0.75rem",
              borderRadius: 4,
              fontSize: "0.8rem",
              overflow: "auto",
              border: "1px solid #30363d",
            }}
          >
            {dFlags.join("\n")}
          </pre>
        )}
      </aside>
      <section>
        <RenderStatusLine state={renderState} />
        {renderState.kind === "ok" && <StlViewer stl={renderState.stl} />}
        {renderState.kind === "rendering" && (
          <div style={placeholderStyle}>rendering…</div>
        )}
        {renderState.kind === "error" && (
          <div style={{ ...placeholderStyle, color: "#ffb4b4" }}>
            <strong>render failed</strong>
            <pre style={{ marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
              {renderState.result.errorMessage}
              {"\n\n"}
              {renderState.result.stderr.slice(-12).join("\n")}
            </pre>
          </div>
        )}
        {renderState.kind === "idle" && <div style={placeholderStyle}>idle</div>}
      </section>
    </div>
  );
}

const placeholderStyle: React.CSSProperties = {
  height: 480,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 4,
};

type RenderState =
  | { kind: "idle" }
  | { kind: "rendering"; since: number }
  | { kind: "ok"; result: RenderResult; stl: Uint8Array }
  | { kind: "error"; result: RenderResult };

function RenderStatusLine({ state }: { state: RenderState }) {
  if (state.kind === "ok") {
    const { result } = state;
    return (
      <div style={statusStyle}>
        rendered in {result.wallMs.toFixed(0)}ms · {result.stl?.length.toLocaleString()} bytes ·
        {" "}{result.filesMounted} libs mounted
        {result.missing.length > 0 && ` · ${result.missing.length} missing`}
      </div>
    );
  }
  if (state.kind === "rendering") {
    return <div style={statusStyle}>rendering…</div>;
  }
  if (state.kind === "error") {
    return <div style={{ ...statusStyle, color: "#ffb4b4" }}>error</div>;
  }
  return <div style={statusStyle}>—</div>;
}

const statusStyle: React.CSSProperties = {
  fontSize: "0.85rem",
  color: "#8b949e",
  marginBottom: "0.5rem",
  fontFamily: "ui-monospace, monospace",
};

// Browser-side fetcher used by the closure walker. Don't pre-encode
// the path — searchParams handles it, and the server route's allow
// regex expects literal slashes.
async function fetchLibFromApi(relPath: string): Promise<string | null> {
  const url = new URL("/api/source", window.location.origin);
  url.searchParams.set("path", `libs/${relPath}`);
  const res = await fetch(url.toString());
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`fetch ${relPath}: ${res.status}`);
  return res.text();
}
