// Direction A — "Caliper" v2
// Dark pro-tool, Linear-compact density. Warm off-white accent for signal.
// IBM Plex Sans + Mono.

const C = {
  bg: "#0c0d10",
  panel: "#131418",
  panel2: "#181a1f",
  panelHi: "#1d1f25",
  line: "#22252c",
  lineSoft: "#1a1c21",
  text: "#e7e2d6",
  textDim: "#8a8578",
  textMute: "#555147",
  accent: "#e7e2d6",       // warm off-white signal
  accentInk: "#0c0d10",
  accentSoft: "#e7e2d614",
  accentLine: "#e7e2d644",
  red: "#d96a6a",
  green: "#8ee29d",
  blue: "#7ab6ff",
  warn: "#f0c06a",
};

const iconBtn = {
  background: "transparent", border: `1px solid ${C.line}`, color: C.textDim,
  width: 24, height: 24, borderRadius: 4, display: "inline-flex", alignItems: "center", justifyContent: "center",
  cursor: "pointer", padding: 0,
};
const iconBtnGhost = { ...iconBtn, border: "none" };

function Kbd({ children }) {
  return <span className="mono" style={{ fontSize: 10, padding: "1px 5px", border: `1px solid ${C.line}`, borderRadius: 3, color: C.textDim, background: C.panel2 }}>{children}</span>;
}

function CaliperChrome({ crumbs, rightSlot, children, onBack, onOpenCmd }) {
  return (
    <div className="caliper" style={{ background: C.bg, color: C.text, width: "100%", height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", fontSize: 13 }}>
      <div style={{ height: 38, display: "flex", alignItems: "center", borderBottom: `1px solid ${C.line}`, padding: "0 12px", gap: 12, background: C.panel }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="1" width="12" height="12" stroke={C.accent} strokeWidth="1.2" />
            <path d="M1 5h12M1 9h12M5 1v12M9 1v12" stroke={C.accent} strokeWidth="0.6" opacity="0.5" />
          </svg>
          <span style={{ fontWeight: 600, letterSpacing: "0.08em", fontSize: 11 }}>STUFF</span>
          <span className="mono" style={{ color: C.textMute, fontSize: 10 }}>0.4.2</span>
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: C.textDim }} className="mono">
          {onBack && (
            <button onClick={onBack} style={{ background: "transparent", border: "none", color: C.textDim, display: "flex", alignItems: "center", gap: 3, cursor: "pointer", padding: "2px 4px", fontSize: 11 }}>
              <Icon name="arrow-left" size={12} /> library
            </button>
          )}
          {crumbs && <span>{crumbs}</span>}
        </div>
        <button onClick={onOpenCmd} style={{
          display: "flex", alignItems: "center", gap: 8,
          background: C.panel2, border: `1px solid ${C.line}`, color: C.textDim,
          padding: "3px 8px 3px 8px", borderRadius: 4, fontSize: 11, cursor: "pointer", minWidth: 180,
        }}>
          <Icon name="search" size={12} />
          <span style={{ flex: 1, textAlign: "left" }}>Search or jump to…</span>
          <Kbd>⌘K</Kbd>
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 4, color: C.textDim }}>
          {rightSlot}
        </div>
      </div>
      {children}
    </div>
  );
}

/* ============================================================== */
/* Home                                                           */
/* ============================================================== */

function CaliperHome({ onOpen, onOpenCmd }) {
  const [view, setView] = React.useState("grid");
  const [filter, setFilter] = React.useState("All");
  const filters = ["All", "Multiboard", "Toys & Replacements", "Household & Misc"];

  return (
    <CaliperChrome
      crumbs={<span>~/ <span style={{ color: C.text }}>library</span></span>}
      onOpenCmd={onOpenCmd}
      rightSlot={
        <div style={{ display: "flex", border: `1px solid ${C.line}`, borderRadius: 4 }}>
          <button onClick={() => setView("grid")} style={{ ...iconBtnGhost, borderRight: `1px solid ${C.line}`, color: view === "grid" ? C.accent : C.textDim, borderRadius: 0 }}><Icon name="grid" size={12} /></button>
          <button onClick={() => setView("list")} style={{ ...iconBtnGhost, color: view === "list" ? C.accent : C.textDim, borderRadius: 0 }}><Icon name="list" size={12} /></button>
        </div>
      }
    >
      <div style={{ flex: 1, overflow: "auto" }}>
        {/* Header band */}
        <div style={{ padding: "18px 22px 16px", borderBottom: `1px solid ${C.line}`, display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 24 }}>
          <div>
            <div className="mono" style={{ color: C.textMute, fontSize: 10, letterSpacing: "0.12em", marginBottom: 6 }}>LIBRARY · 8 MODELS · 3 SHELVES</div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, letterSpacing: "-0.015em" }}>
              Parametric things.
              <span style={{ color: C.textDim, fontWeight: 400 }}> Tweak. Render. Print.</span>
            </h1>
          </div>
          <div className="mono" style={{ color: C.textMute, fontSize: 10, textAlign: "right", lineHeight: 1.6 }}>
            openscad-wasm · manifold<br/>
            last sync 2m ago
          </div>
        </div>

        {/* Filters */}
        <div style={{ padding: "10px 22px", display: "flex", alignItems: "center", gap: 6, borderBottom: `1px solid ${C.line}`, background: C.panel }}>
          <div className="mono" style={{ fontSize: 10, color: C.textMute, letterSpacing: "0.08em", marginRight: 4 }}>FILTER</div>
          {filters.map((t) => (
            <button key={t} onClick={() => setFilter(t)} style={{
              fontSize: 11, padding: "3px 9px", borderRadius: 999,
              border: `1px solid ${filter === t ? C.accentLine : C.line}`,
              color: filter === t ? C.accent : C.textDim,
              background: filter === t ? C.accentSoft : "transparent",
              cursor: "pointer",
            }}>{t}</button>
          ))}
          <div style={{ flex: 1 }} />
          <div className="mono" style={{ fontSize: 10, color: C.textMute }}>SORT</div>
          <button style={{ ...iconBtn, width: "auto", padding: "0 8px", height: 22, fontSize: 11, color: C.textDim, gap: 4 }} className="mono">
            recent <Icon name="chevron-down" size={10} />
          </button>
        </div>

        <div style={{ padding: "20px 22px 40px" }}>
          {MODEL_CATEGORIES.map((cat) => <Shelf key={cat.id} cat={cat} onOpen={onOpen} view={view} />)}
        </div>
      </div>
    </CaliperChrome>
  );
}

function Shelf({ cat, onOpen, view }) {
  const items = MODELS[cat.id];
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10, paddingBottom: 6, borderBottom: `1px solid ${C.line}` }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <div className="mono" style={{ fontSize: 10, color: C.textMute }}>§{String(MODEL_CATEGORIES.indexOf(cat) + 1).padStart(2, "0")}</div>
          <h2 style={{ margin: 0, fontSize: 13, fontWeight: 600 }}>{cat.label}</h2>
          <span className="mono" style={{ fontSize: 10, color: C.textMute }}>{cat.count}</span>
        </div>
        <div style={{ fontSize: 11, color: C.textDim, maxWidth: 460, textAlign: "right" }}>{cat.note}</div>
      </div>

      {view === "grid" ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {items.map((m) => <ModelCard key={m.slug} m={m} onOpen={onOpen} />)}
        </div>
      ) : (
        <div style={{ border: `1px solid ${C.line}`, borderRadius: 4, overflow: "hidden" }}>
          {items.map((m, i) => <ModelRow key={m.slug} m={m} onOpen={onOpen} last={i === items.length - 1} />)}
        </div>
      )}
    </div>
  );
}

function ModelCard({ m, onOpen }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button
      onClick={() => onOpen(m)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        textAlign: "left", cursor: "pointer", background: C.panel, color: C.text,
        border: `1px solid ${hover ? C.accentLine : C.line}`, borderRadius: 4, padding: 0,
        display: "flex", flexDirection: "column", transition: "border-color 120ms, background 120ms",
      }}
    >
      <div style={{ aspectRatio: "5 / 3", borderBottom: `1px solid ${C.line}`, background: `linear-gradient(180deg, ${C.panel2}, ${C.bg})`, position: "relative", overflow: "hidden" }}>
        <svg width="100%" height="100%" style={{ position: "absolute", inset: 0, opacity: 0.55 }}>
          <defs>
            <pattern id={`cal-grid-${m.slug}`} width="16" height="16" patternUnits="userSpaceOnUse">
              <path d="M 16 0 L 0 0 0 16" fill="none" stroke={C.lineSoft} strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill={`url(#cal-grid-${m.slug})`} />
        </svg>
        <div style={{ position: "absolute", inset: 0, padding: "14% 18%" }}>
          <ModelGlyph slug={m.slug} accent={C.accent} muted={C.textMute} />
        </div>
        <div className="mono" style={{ position: "absolute", left: 8, top: 8, fontSize: 9, color: C.textMute, letterSpacing: "0.06em" }}>
          {m.stem.replace(".scad", "").toUpperCase()}
        </div>
        <div className="mono" style={{ position: "absolute", right: 8, bottom: 8, fontSize: 9, color: C.textMute }}>{m.size}</div>
      </div>
      <div style={{ padding: "9px 11px 10px" }}>
        <div style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.25 }}>{m.title}</div>
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 3, lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{m.blurb}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }} className="mono">
          <span style={{ fontSize: 9, color: C.accent, display: "flex", alignItems: "center", gap: 3 }}>
            <Icon name="slider" size={10} stroke={C.accent} /> {m.paramCount}
          </span>
          <span style={{ fontSize: 9, color: C.textMute }}>{m.presets.length} presets</span>
        </div>
      </div>
    </button>
  );
}

function ModelRow({ m, onOpen, last }) {
  const [hover, setHover] = React.useState(false);
  return (
    <button onClick={() => onOpen(m)}
      onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ width: "100%", background: hover ? C.panel : "transparent", color: C.text, border: "none", borderBottom: last ? "none" : `1px solid ${C.line}`, display: "grid", gridTemplateColumns: "36px 1.5fr 2.2fr 70px 90px 20px", alignItems: "center", padding: "8px 14px", textAlign: "left", cursor: "pointer", gap: 14 }}>
      <div style={{ width: 36, height: 26, border: `1px solid ${C.line}`, borderRadius: 3, background: C.panel2, padding: 3 }}>
        <ModelGlyph slug={m.slug} accent={C.accent} muted={C.textMute} />
      </div>
      <div>
        <div style={{ fontSize: 12, fontWeight: 600 }}>{m.title}</div>
        <div className="mono" style={{ fontSize: 9, color: C.textMute, marginTop: 1 }}>{m.stem}</div>
      </div>
      <div style={{ fontSize: 11, color: C.textDim, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.blurb}</div>
      <div className="mono" style={{ fontSize: 10, color: C.textDim }}>{m.paramCount} params</div>
      <div className="mono" style={{ fontSize: 10, color: C.textMute }}>{m.size}</div>
      <Icon name="chevron-right" size={12} style={{ color: C.textMute }} />
    </button>
  );
}

/* ============================================================== */
/* Detail — Desktop                                               */
/* ============================================================== */

function CaliperDetail({ m, onBack, onOpenCmd, onOpenPrint, initialState }) {
  const [values, setValues] = React.useState(() => {
    const v = {};
    PARAM_GROUPS.forEach(g => g.params.forEach(p => { v[p.name] = p.value; }));
    return v;
  });
  const [activePreset, setActivePreset] = React.useState("70");
  const [view, setView] = React.useState("iso");
  const [wireframe, setWireframe] = React.useState(false);
  const [showGrid, setShowGrid] = React.useState(true);
  const [showDims, setShowDims] = React.useState(true);
  const [state, setState] = React.useState(initialState || "ok"); // ok | loading | error | empty

  return (
    <CaliperChrome
      onBack={onBack}
      onOpenCmd={onOpenCmd}
      crumbs={<span>~/ library / <span style={{ color: C.text }}>{m.stem}</span></span>}
      rightSlot={
        <>
          <button style={{ ...iconBtn, width: "auto", padding: "0 8px", gap: 5, color: C.textDim, fontSize: 11, height: 24 }} className="mono">
            <Icon name="share" size={11} /> share
          </button>
          <button onClick={onOpenPrint} style={{
            background: "transparent", color: C.text, border: `1px solid ${C.line}`,
            padding: "3px 10px", borderRadius: 4, fontSize: 11, fontWeight: 500, cursor: "pointer",
            display: "inline-flex", alignItems: "center", gap: 5, height: 24,
          }}>
            <Icon name="cube" size={11} /> Print prep
          </button>
          <button style={{
            background: C.accent, color: C.accentInk, border: "none", padding: "4px 11px", borderRadius: 4,
            fontSize: 11, fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 5, height: 24,
          }}>
            <Icon name="download" size={11} stroke={C.accentInk} /> Download STL
          </button>
        </>
      }
    >
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "240px 1fr 280px", minHeight: 0 }}>

        {/* LEFT */}
        <aside style={{ borderRight: `1px solid ${C.line}`, padding: "14px 14px 16px", overflow: "auto", display: "flex", flexDirection: "column", gap: 18, background: C.panel }}>
          <div>
            <SectionLabel>Presets</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 3, marginTop: 8 }}>
              {PRESETS.map(p => (
                <button key={p.id}
                  onClick={() => setActivePreset(p.id)}
                  style={{
                    textAlign: "left",
                    background: activePreset === p.id ? C.accentSoft : "transparent",
                    border: `1px solid ${activePreset === p.id ? C.accentLine : C.line}`,
                    borderRadius: 3, padding: "6px 8px", color: C.text, cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 8,
                  }}>
                  <div className="mono" style={{ fontSize: 10, width: 26, color: activePreset === p.id ? C.accent : C.textMute }}>{p.id}mm</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 500 }}>{p.name}</div>
                    <div style={{ fontSize: 9, color: C.textMute, marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{p.sub}</div>
                  </div>
                  {activePreset === p.id && <Icon name="check" size={11} stroke={C.accent} />}
                </button>
              ))}
              <button style={{ textAlign: "left", background: "transparent", border: `1px dashed ${C.line}`, borderRadius: 3, padding: "6px 8px", color: C.textDim, cursor: "pointer", fontSize: 11, display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
                <Icon name="plus" size={11} /> Save as preset
              </button>
            </div>
          </div>

          <div>
            <SectionLabel>Model notes</SectionLabel>
            <div style={{ fontSize: 11, color: C.textDim, lineHeight: 1.5, marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
              {MODEL_NOTES.map((n, i) => (
                <div key={i} style={{ display: "flex", gap: 7 }}>
                  <span className="mono" style={{ color: C.textMute, fontSize: 9, minWidth: 12, marginTop: 2 }}>{String(i + 1).padStart(2, "0")}</span>
                  <span>{n}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <SectionLabel>Source</SectionLabel>
            <div className="mono" style={{ fontSize: 10, color: C.textDim, marginTop: 8, lineHeight: 1.7 }}>
              <div style={{ color: C.text }}>{m.stem}</div>
              <div style={{ color: C.textMute }}>BOSL2 · QuackWorks</div>
              <div style={{ color: C.textMute }}>$fn = 64</div>
              <button style={{ background: "transparent", border: "none", color: C.textDim, cursor: "pointer", padding: 0, marginTop: 4, display: "flex", alignItems: "center", gap: 4, fontSize: 10 }}>
                <Icon name="copy" size={10} /> view source
              </button>
            </div>
          </div>
        </aside>

        {/* CENTER */}
        <section style={{ display: "flex", flexDirection: "column", minHeight: 0, background: C.bg }}>
          <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
            {showGrid && <ViewerGrid />}

            {state === "ok" && (
              <>
                <div style={{ position: "absolute", inset: 0, padding: "8% 16% 10%" }}>
                  <HolderGlyph accent={C.accent} muted={C.textMute} showRule={showDims} />
                </div>
                <AxesIndicator />
              </>
            )}
            {state === "loading" && <LoadingOverlay />}
            {state === "error" && <ErrorOverlay />}
            {state === "empty" && <EmptyOverlay />}

            {/* Top status strip */}
            <div style={{ position: "absolute", left: 0, right: 0, top: 0, padding: "8px 12px", display: "flex", justifyContent: "space-between", gap: 12 }} className="mono">
              <div style={{ fontSize: 10, color: C.textDim, display: "flex", alignItems: "center", gap: 6 }}>
                {state === "ok" && <><span style={{ width: 6, height: 6, borderRadius: 999, background: C.green, display: "inline-block" }} /> rendered · 2.1s · 78 kb · 3 libs mounted</>}
                {state === "loading" && <><span style={{ width: 6, height: 6, borderRadius: 999, background: C.accent, display: "inline-block" }} /> rendering…</>}
                {state === "error" && <><span style={{ width: 6, height: 6, borderRadius: 999, background: C.red, display: "inline-block" }} /> render failed</>}
                {state === "empty" && <><span style={{ width: 6, height: 6, borderRadius: 999, background: C.textMute, display: "inline-block" }} /> idle</>}
              </div>
              {state === "ok" && (
                <div style={{ fontSize: 10, color: C.textMute, display: "flex", gap: 12 }}>
                  <span>bbox 110 × 60 × 85</span>
                  <span>▲ 12,448</span>
                </div>
              )}
            </div>

            {/* Right toolbar */}
            <div style={{ position: "absolute", right: 10, top: 36, display: "flex", flexDirection: "column", gap: 3, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 4, padding: 3 }}>
              {[["top", "Top"], ["front", "Front"], ["iso", "Iso"]].map(([k, lbl]) => (
                <button key={k} onClick={() => setView(k)} className="mono"
                  style={{ background: view === k ? C.accentSoft : "transparent", color: view === k ? C.accent : C.textDim, border: "none", fontSize: 10, padding: "3px 8px", borderRadius: 2, cursor: "pointer", width: 48, textAlign: "left" }}>
                  {lbl}
                </button>
              ))}
              <div style={{ borderTop: `1px solid ${C.line}`, margin: "2px 0" }} />
              <ToolbarToggle active={showGrid} onClick={() => setShowGrid(g => !g)} icon="grid" />
              <ToolbarToggle active={showDims} onClick={() => setShowDims(d => !d)} icon="axes" />
              <ToolbarToggle active={wireframe} onClick={() => setWireframe(w => !w)} icon="cube" />
              <div style={{ borderTop: `1px solid ${C.line}`, margin: "2px 0" }} />
              <ToolbarToggle icon="expand" />
            </div>

            {/* State selector (for demo) */}
            <div style={{ position: "absolute", right: 10, bottom: 10, display: "flex", gap: 3, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 4, padding: 2 }} className="mono">
              {["ok", "loading", "error", "empty"].map(s => (
                <button key={s} onClick={() => setState(s)} style={{
                  background: state === s ? C.accentSoft : "transparent",
                  color: state === s ? C.accent : C.textMute,
                  border: "none", fontSize: 9, padding: "2px 6px", borderRadius: 2, cursor: "pointer",
                }}>{s}</button>
              ))}
            </div>
          </div>

          {/* Stats bar */}
          <div style={{ borderTop: `1px solid ${C.line}`, padding: "6px 14px", display: "flex", gap: 18, background: C.panel, alignItems: "center" }} className="mono">
            <Stat label="DIAM" value={`${values.can_diameter} mm`} />
            <Stat label="H" value={`${values.ring_height} mm`} />
            <Stat label="WALL" value={`${values.wall} mm`} />
            <Stat label="ARC" value={`${values.front_opening_deg}°`} />
            <Stat label="SLOTS" value={values.slot_count} />
            <div style={{ flex: 1 }} />
            <Stat label="PRINT" value="1h 42m" accent />
            <Stat label="FIL" value="14.8 g" />
          </div>
        </section>

        {/* RIGHT */}
        <aside style={{ borderLeft: `1px solid ${C.line}`, overflow: "auto", display: "flex", flexDirection: "column", background: C.panel }}>
          <div style={{ padding: "11px 14px", borderBottom: `1px solid ${C.line}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{m.title}</div>
              <div className="mono" style={{ fontSize: 9, color: C.textMute, marginTop: 2 }}>{m.paramCount} parameters · 3 groups</div>
            </div>
            <button style={iconBtn}><Icon name="copy" size={12} /></button>
          </div>
          <div>
            {PARAM_GROUPS.map(g => <ParamGroup key={g.id} group={g} values={values} setValues={setValues} />)}
          </div>
        </aside>
      </div>
    </CaliperChrome>
  );
}

function ToolbarToggle({ active, onClick, icon }) {
  return (
    <button onClick={onClick} style={{
      background: active ? C.accentSoft : "transparent",
      color: active ? C.accent : C.textDim,
      border: "none", padding: "4px 6px", borderRadius: 2, cursor: "pointer",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <Icon name={icon} size={12} />
    </button>
  );
}

function ViewerGrid() {
  return (
    <svg width="100%" height="100%" style={{ position: "absolute", inset: 0 }}>
      <defs>
        <pattern id="cal-viewer-fine" width="8" height="8" patternUnits="userSpaceOnUse">
          <path d="M 8 0 L 0 0 0 8" fill="none" stroke="#141519" strokeWidth="0.5" />
        </pattern>
        <pattern id="cal-viewer-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke={C.lineSoft} strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#cal-viewer-fine)" />
      <rect width="100%" height="100%" fill="url(#cal-viewer-grid)" />
    </svg>
  );
}

function AxesIndicator() {
  return (
    <div style={{ position: "absolute", left: 12, bottom: 12 }} className="mono">
      <svg width="64" height="64" viewBox="0 0 72 72">
        <line x1="20" y1="52" x2="50" y2="52" stroke={C.red} strokeWidth="1.2" />
        <text x="54" y="55" fill={C.red} fontSize="9">X</text>
        <line x1="20" y1="52" x2="20" y2="22" stroke={C.green} strokeWidth="1.2" />
        <text x="14" y="20" fill={C.green} fontSize="9">Z</text>
        <line x1="20" y1="52" x2="38" y2="64" stroke={C.blue} strokeWidth="1.2" />
        <text x="40" y="68" fill={C.blue} fontSize="9">Y</text>
      </svg>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
        <svg width="32" height="32" viewBox="0 0 32 32">
          <circle cx="16" cy="16" r="12" fill="none" stroke={C.line} strokeWidth="1.5" />
          <circle cx="16" cy="16" r="12" fill="none" stroke={C.accent} strokeWidth="1.5" strokeDasharray="18 60" strokeLinecap="round">
            <animateTransform attributeName="transform" type="rotate" from="0 16 16" to="360 16 16" dur="1s" repeatCount="indefinite" />
          </circle>
        </svg>
        <div className="mono" style={{ fontSize: 11, color: C.textDim }}>compiling OpenSCAD…</div>
        <div className="mono" style={{ fontSize: 9, color: C.textMute }}>mounting 3 libs · running manifold</div>
      </div>
    </div>
  );
}

function ErrorOverlay() {
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div style={{ maxWidth: 520, border: `1px solid ${C.red}44`, background: `${C.red}0d`, borderRadius: 4, padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Icon name="x" size={12} stroke={C.red} />
          <span style={{ fontSize: 12, color: C.red, fontWeight: 600 }}>Render failed</span>
          <span className="mono" style={{ fontSize: 10, color: C.textMute, marginLeft: "auto" }}>after 0.8 s</span>
        </div>
        <pre className="mono" style={{ margin: 0, fontSize: 10, color: C.textDim, whiteSpace: "pre-wrap", lineHeight: 1.55 }}>
{`ERROR: Parser error in file
  cylindrical_holder_slot.scad, line 34
  can_diameter cannot exceed 200 mm

  32 |  can_diameter = 250;
  33 |  ring_height  = 35;
  34 |  ↑ value out of range (min 20, max 200)`}
        </pre>
        <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
          <button style={{ background: C.accent, color: C.accentInk, border: "none", padding: "4px 10px", borderRadius: 3, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
            Revert last change
          </button>
          <button style={{ background: "transparent", color: C.textDim, border: `1px solid ${C.line}`, padding: "4px 10px", borderRadius: 3, fontSize: 11, cursor: "pointer" }}>
            Copy stderr
          </button>
        </div>
      </div>
    </div>
  );
}

function EmptyOverlay() {
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", color: C.textMute }}>
        <Icon name="cube" size={40} stroke={C.textMute} />
        <div style={{ fontSize: 12, marginTop: 10, color: C.textDim }}>No render yet.</div>
        <div className="mono" style={{ fontSize: 10, marginTop: 4 }}>tweak a parameter to start</div>
      </div>
    </div>
  );
}

function SectionLabel({ children }) {
  return <div className="mono" style={{ fontSize: 9, letterSpacing: "0.12em", color: C.textMute, textTransform: "uppercase" }}>{children}</div>;
}

function Stat({ label, value, accent }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
      <div style={{ fontSize: 9, color: C.textMute, letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ fontSize: 11, color: accent ? C.accent : C.text }}>{value}</div>
    </div>
  );
}

function ParamGroup({ group, values, setValues }) {
  const [open, setOpen] = React.useState(true);
  return (
    <div style={{ borderBottom: `1px solid ${C.line}` }}>
      <button onClick={() => setOpen(o => !o)}
        style={{ width: "100%", background: "transparent", border: "none", color: C.text, padding: "9px 14px 7px", display: "flex", alignItems: "center", gap: 6, cursor: "pointer", textAlign: "left" }}>
        <Icon name={open ? "chevron-down" : "chevron-right"} size={11} style={{ color: C.textMute }} />
        <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>{group.label}</span>
        <span className="mono" style={{ fontSize: 9, color: C.textMute, marginLeft: 2 }}>{group.params.length}</span>
      </button>
      {open && (
        <div style={{ padding: "2px 14px 12px", display: "flex", flexDirection: "column", gap: 10 }}>
          {group.params.map(p => <ParamControl key={p.name} param={p} value={values[p.name]} onChange={(v) => setValues(s => ({ ...s, [p.name]: v }))} />)}
        </div>
      )}
    </div>
  );
}

function ParamControl({ param, value, onChange }) {
  if (param.kind === "boolean") {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "2px 0" }}>
        <div style={{ fontSize: 11 }}>{param.label}</div>
        <button onClick={() => onChange(!value)} style={{
          width: 28, height: 16, borderRadius: 999, border: `1px solid ${value ? C.accentLine : C.line}`,
          background: value ? C.accent : "transparent", position: "relative", cursor: "pointer", padding: 0,
        }}>
          <div style={{ width: 10, height: 10, borderRadius: 999, background: value ? C.accentInk : C.textMute, position: "absolute", top: 2, left: value ? 15 : 2, transition: "left 120ms" }} />
        </button>
      </div>
    );
  }
  const pct = ((value - param.min) / (param.max - param.min)) * 100;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
        <div style={{ fontSize: 11, color: C.text }}>{param.label}</div>
        <div className="mono" style={{ fontSize: 10, color: C.accent }}>
          {value}<span style={{ color: C.textMute, marginLeft: 2 }}>{param.unit}</span>
        </div>
      </div>
      <div style={{ position: "relative", height: 14, display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: C.line, borderRadius: 999 }} />
        <div style={{ position: "absolute", left: 0, width: `${pct}%`, height: 2, background: C.accent, borderRadius: 999 }} />
        <div style={{ position: "absolute", left: `calc(${pct}% - 5px)`, width: 10, height: 10, borderRadius: 999, background: C.accent, border: `2px solid ${C.panel}` }} />
        <input type="range" min={param.min} max={param.max} step={param.step || 1} value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0, cursor: "pointer" }} />
      </div>
      <div className="mono" style={{ display: "flex", justifyContent: "space-between", marginTop: 2, fontSize: 8, color: C.textMute }}>
        <span>{param.min}</span><span>{param.name}</span><span>{param.max}</span>
      </div>
    </div>
  );
}

/* ============================================================== */
/* Print-prep                                                     */
/* ============================================================== */

function CaliperPrintPrep({ m, onBack, onOpenCmd }) {
  const [orient, setOrient] = React.useState("back-down");
  const [infill, setInfill] = React.useState(20);
  const [layer, setLayer] = React.useState(0.2);
  const [supports, setSupports] = React.useState(true);
  const [copies, setCopies] = React.useState(1);
  return (
    <CaliperChrome
      onBack={onBack}
      onOpenCmd={onOpenCmd}
      crumbs={<span>~/ library / {m.stem} / <span style={{ color: C.text }}>print prep</span></span>}
      rightSlot={
        <>
          <button style={{
            background: "transparent", color: C.text, border: `1px solid ${C.line}`,
            padding: "3px 10px", borderRadius: 4, fontSize: 11, fontWeight: 500, cursor: "pointer",
            display: "inline-flex", alignItems: "center", gap: 5, height: 24,
          }}>
            <Icon name="download" size={11} /> Export 3MF
          </button>
          <button style={{
            background: C.accent, color: C.accentInk, border: "none", padding: "4px 11px", borderRadius: 4,
            fontSize: 11, fontWeight: 600, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 5, height: 24,
          }}>
            <Icon name="share" size={11} stroke={C.accentInk} /> Send to PrusaSlicer
          </button>
        </>
      }
    >
      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 320px", minHeight: 0 }}>
        <section style={{ position: "relative", background: C.bg, overflow: "hidden" }}>
          {/* build plate */}
          <svg width="100%" height="100%" viewBox="0 0 800 520" style={{ position: "absolute", inset: 0 }}>
            <defs>
              <pattern id="plate-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke={C.lineSoft} strokeWidth="0.8" />
              </pattern>
            </defs>
            {/* perspective build plate */}
            <g transform="translate(400 320)">
              <polygon points="-280,-100 280,-100 360,100 -360,100" fill={C.panel2} stroke={C.line} strokeWidth="1" />
              <polygon points="-280,-100 280,-100 360,100 -360,100" fill="url(#plate-grid)" opacity="0.6" />
              {/* origin */}
              <circle cx="-260" cy="-88" r="3" fill={C.red} />
              <text x="-252" y="-84" fill={C.red} fontSize="9" fontFamily="IBM Plex Mono">0,0</text>
              {/* plate label */}
              <text x="0" y="90" fill={C.textMute} fontSize="10" fontFamily="IBM Plex Mono" textAnchor="middle">250 × 210 mm — MK4</text>
            </g>

            {/* model on plate */}
            <g transform="translate(400 230)">
              <g transform="scale(1.3)">
                <ellipse cx="0" cy="54" rx="48" ry="9" fill="none" stroke={C.accent} strokeWidth="1.4" />
                <ellipse cx="0" cy="-8" rx="48" ry="9" fill="none" stroke={C.accent} strokeWidth="1.4" />
                <line x1="-48" y1="-8" x2="-48" y2="54" stroke={C.accent} strokeWidth="1.4" />
                <line x1="48" y1="-8" x2="48" y2="54" stroke={C.accent} strokeWidth="1.4" />
                <rect x="-38" y="-70" width="76" height="66" fill="none" stroke={C.textDim} strokeWidth="1" />
                <rect x="-18" y="-56" width="36" height="5" fill="none" stroke={C.textDim} strokeWidth="0.8" />
                <rect x="-18" y="-40" width="36" height="5" fill="none" stroke={C.textDim} strokeWidth="0.8" />
                <rect x="-18" y="-24" width="36" height="5" fill="none" stroke={C.textDim} strokeWidth="0.8" />
              </g>
              {/* bbox */}
              <rect x="-75" y="-108" width="150" height="180" fill="none" stroke={C.accentLine} strokeWidth="1" strokeDasharray="3 3" />
            </g>

            {/* dimension lines */}
            <g fontFamily="IBM Plex Mono" fontSize="10" fill={C.textMute}>
              <line x1="325" y1="330" x2="475" y2="330" stroke={C.textMute} strokeWidth="0.5" />
              <line x1="325" y1="326" x2="325" y2="334" stroke={C.textMute} strokeWidth="0.5" />
              <line x1="475" y1="326" x2="475" y2="334" stroke={C.textMute} strokeWidth="0.5" />
              <text x="400" y="345" textAnchor="middle">110 mm</text>
            </g>
          </svg>

          {/* top strip */}
          <div className="mono" style={{ position: "absolute", top: 8, left: 12, fontSize: 10, color: C.textDim }}>● plate · Prusa MK4 · 250 × 210 × 220</div>

          <AxesIndicator />
        </section>

        <aside style={{ borderLeft: `1px solid ${C.line}`, background: C.panel, overflow: "auto", padding: "14px 14px 20px", display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <SectionLabel>Summary</SectionLabel>
            <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <BigStatC label="PRINT TIME" value="1h 42m" accent />
              <BigStatC label="FILAMENT" value="14.8 g" />
              <BigStatC label="LAYERS" value="176" />
              <BigStatC label="COST (est)" value="$0.37" />
            </div>
          </div>

          <div>
            <SectionLabel>Orientation</SectionLabel>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, marginTop: 8 }}>
              {[
                ["back-down", "Back-down", "recommended"],
                ["upright", "Upright", "more supports"],
                ["flat", "Cradle-flat", "experimental"],
                ["auto", "Auto-orient", "minimize supports"],
              ].map(([k, name, hint]) => (
                <button key={k} onClick={() => setOrient(k)} style={{
                  textAlign: "left", padding: "6px 8px", borderRadius: 3,
                  background: orient === k ? C.accentSoft : "transparent",
                  border: `1px solid ${orient === k ? C.accentLine : C.line}`,
                  color: C.text, cursor: "pointer",
                }}>
                  <div style={{ fontSize: 11, fontWeight: 500 }}>{name}</div>
                  <div className="mono" style={{ fontSize: 9, color: orient === k ? C.accent : C.textMute, marginTop: 1 }}>{hint}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <SectionLabel>Print settings</SectionLabel>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 12 }}>
              <PrintSlider label="Layer height" value={layer} unit="mm" min={0.1} max={0.3} step={0.05} onChange={setLayer} />
              <PrintSlider label="Infill" value={infill} unit="%" min={0} max={100} step={5} onChange={setInfill} />
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontSize: 11 }}>Supports</div>
                <button onClick={() => setSupports(s => !s)} style={{
                  width: 28, height: 16, borderRadius: 999, border: `1px solid ${supports ? C.accentLine : C.line}`,
                  background: supports ? C.accent : "transparent", position: "relative", cursor: "pointer", padding: 0,
                }}>
                  <div style={{ width: 10, height: 10, borderRadius: 999, background: supports ? C.accentInk : C.textMute, position: "absolute", top: 2, left: supports ? 15 : 2 }} />
                </button>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontSize: 11 }}>Copies on plate</div>
                <div style={{ display: "flex", alignItems: "center", gap: 4, border: `1px solid ${C.line}`, borderRadius: 3 }}>
                  <button onClick={() => setCopies(c => Math.max(1, c - 1))} style={{ ...iconBtnGhost, width: 20, height: 20 }}><Icon name="minus" size={10} /></button>
                  <span className="mono" style={{ fontSize: 11, minWidth: 16, textAlign: "center" }}>{copies}</span>
                  <button onClick={() => setCopies(c => c + 1)} style={{ ...iconBtnGhost, width: 20, height: 20 }}><Icon name="plus" size={10} /></button>
                </div>
              </div>
            </div>
          </div>

          <div>
            <SectionLabel>Slicer handoff</SectionLabel>
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
              {[
                ["PrusaSlicer", "open directly"],
                ["OrcaSlicer", "via 3MF"],
                ["Bambu Studio", "via 3MF"],
                ["Cura", "via STL"],
              ].map(([n, hint]) => (
                <button key={n} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 8px", border: `1px solid ${C.line}`, borderRadius: 3, background: "transparent", color: C.text, cursor: "pointer", textAlign: "left" }}>
                  <div>
                    <div style={{ fontSize: 11 }}>{n}</div>
                    <div className="mono" style={{ fontSize: 9, color: C.textMute, marginTop: 1 }}>{hint}</div>
                  </div>
                  <Icon name="chevron-right" size={11} style={{ color: C.textMute }} />
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </CaliperChrome>
  );
}

function BigStatC({ label, value, accent }) {
  return (
    <div style={{ border: `1px solid ${C.line}`, borderRadius: 3, padding: "8px 10px", background: C.panel2 }}>
      <div className="mono" style={{ fontSize: 9, color: C.textMute, letterSpacing: "0.08em" }}>{label}</div>
      <div style={{ fontSize: 15, color: accent ? C.accent : C.text, marginTop: 3, fontWeight: 500 }}>{value}</div>
    </div>
  );
}

function PrintSlider({ label, value, unit, min, max, step, onChange }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4 }}>
        <div style={{ fontSize: 11 }}>{label}</div>
        <div className="mono" style={{ fontSize: 10, color: C.accent }}>{value}<span style={{ color: C.textMute }}>{unit}</span></div>
      </div>
      <div style={{ position: "relative", height: 14, display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: 0, right: 0, height: 2, background: C.line, borderRadius: 999 }} />
        <div style={{ position: "absolute", left: 0, width: `${pct}%`, height: 2, background: C.accent, borderRadius: 999 }} />
        <div style={{ position: "absolute", left: `calc(${pct}% - 5px)`, width: 10, height: 10, borderRadius: 999, background: C.accent, border: `2px solid ${C.panel}` }} />
        <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0, cursor: "pointer" }} />
      </div>
    </div>
  );
}

/* ============================================================== */
/* Command palette                                                */
/* ============================================================== */

function CaliperCmdK({ onBack, onOpenCmd }) {
  const [q, setQ] = React.useState("");
  const [active, setActive] = React.useState(2);
  const items = [
    { kind: "model", icon: "cube", name: "Cylindrical Holder — Slot", hint: "models · multiboard · 11 params" },
    { kind: "model", icon: "cube", name: "Parts Tray", hint: "models · multiboard" },
    { kind: "preset", icon: "star", name: "70mm spraycan", hint: "preset · cylindrical_holder_slot" },
    { kind: "preset", icon: "star", name: "77mm spraycan", hint: "preset · cylindrical_holder_slot" },
    { kind: "action", icon: "download", name: "Download current as STL", hint: "action · ⌘E" },
    { kind: "action", icon: "share", name: "Copy share link with params", hint: "action · ⌘⇧C" },
    { kind: "action", icon: "cube", name: "Open print prep", hint: "action · ⌘P" },
    { kind: "nav", icon: "grid", name: "Go to library", hint: "navigate · ⌘L" },
  ];
  return (
    <CaliperChrome onBack={onBack} onOpenCmd={onOpenCmd} crumbs={<span>~/ library / cylindrical_holder_slot.scad</span>}>
      <div style={{ flex: 1, position: "relative", background: C.bg }}>
        {/* Blurred underlayer */}
        <div style={{ position: "absolute", inset: 0, opacity: 0.35, filter: "blur(2px)" }}>
          <ViewerGrid />
          <div style={{ position: "absolute", inset: "12% 22%" }}>
            <HolderGlyph accent={C.accent} muted={C.textMute} />
          </div>
        </div>
        <div style={{ position: "absolute", inset: 0, background: "rgba(10, 12, 15, 0.55)" }} />

        <div style={{ position: "absolute", left: "50%", top: 80, transform: "translateX(-50%)", width: 560, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 6, boxShadow: "0 20px 60px rgba(0,0,0,0.55)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", borderBottom: `1px solid ${C.line}` }}>
            <Icon name="search" size={14} stroke={C.textDim} />
            <input autoFocus value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Search models, presets, actions…"
              style={{ flex: 1, background: "transparent", border: "none", color: C.text, fontSize: 13, outline: "none", fontFamily: "inherit" }} />
            <Kbd>esc</Kbd>
          </div>
          <div style={{ padding: "6px 0", maxHeight: 360, overflow: "auto" }}>
            {["Models", "Presets", "Actions", "Navigate"].map((section, si) => {
              const sectionItems = items.filter((it, idx) => {
                const groups = [["model"], ["preset"], ["action"], ["nav"]];
                return groups[si].includes(it.kind);
              });
              if (!sectionItems.length) return null;
              return (
                <div key={section}>
                  <div className="mono" style={{ fontSize: 9, color: C.textMute, letterSpacing: "0.1em", padding: "8px 14px 4px" }}>{section.toUpperCase()}</div>
                  {sectionItems.map(it => {
                    const idx = items.indexOf(it);
                    const isActive = idx === active;
                    return (
                      <div key={it.name} onMouseEnter={() => setActive(idx)}
                        style={{
                          display: "flex", alignItems: "center", gap: 10, padding: "7px 14px",
                          background: isActive ? C.accentSoft : "transparent",
                          borderLeft: `2px solid ${isActive ? C.accent : "transparent"}`,
                          cursor: "pointer",
                        }}>
                        <Icon name={it.icon} size={13} stroke={isActive ? C.accent : C.textDim} />
                        <div style={{ fontSize: 12, color: isActive ? C.text : C.textDim, flex: 1 }}>{it.name}</div>
                        <div className="mono" style={{ fontSize: 10, color: C.textMute }}>{it.hint}</div>
                      </div>
                    );
                  })}
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "8px 14px", borderTop: `1px solid ${C.line}`, background: C.panel2 }}>
            <div className="mono" style={{ fontSize: 10, color: C.textMute, display: "flex", alignItems: "center", gap: 4 }}>
              <Kbd>↑</Kbd><Kbd>↓</Kbd> navigate
            </div>
            <div className="mono" style={{ fontSize: 10, color: C.textMute, display: "flex", alignItems: "center", gap: 4 }}>
              <Kbd>↵</Kbd> open
            </div>
            <div style={{ flex: 1 }} />
            <div className="mono" style={{ fontSize: 10, color: C.textMute }}>8 results</div>
          </div>
        </div>
      </div>
    </CaliperChrome>
  );
}

/* ============================================================== */
/* Mobile — bottom sheet (committed)                              */
/* ============================================================== */

function CaliperMobile({ m }) {
  const [group, setGroup] = React.useState("cradle");
  const [sheetTall, setSheetTall] = React.useState(false);
  const groupObj = PARAM_GROUPS.find(g => g.id === group);

  return (
    <div className="caliper" style={{ background: C.bg, color: C.text, width: "100%", height: "100%", display: "flex", flexDirection: "column", overflow: "hidden", position: "relative", fontSize: 13 }}>
      <div className="mono" style={{ height: 22, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 14px", fontSize: 10, color: C.textMute, background: C.panel }}>
        <span>9:41</span><span>5G · 82%</span>
      </div>

      {/* viewer */}
      <div style={{ flex: 1, position: "relative" }}>
        <ViewerGrid />
        <div style={{ position: "absolute", inset: `10% 10% ${sheetTall ? "64%" : "44%"}`, display: "flex", alignItems: "center", justifyContent: "center", transition: "inset 180ms" }}>
          <HolderGlyph accent={C.accent} muted={C.textMute} showRule />
        </div>

        {/* top chrome floating */}
        <div style={{ position: "absolute", top: 8, left: 8, right: 8, display: "flex", alignItems: "center", gap: 6 }}>
          <button style={{ ...iconBtn, background: C.panel, width: 28, height: 28 }}><Icon name="arrow-left" size={13} /></button>
          <div style={{ flex: 1, background: `${C.panel}e0`, backdropFilter: "blur(6px)", padding: "5px 10px", borderRadius: 5, border: `1px solid ${C.line}`, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.title}</div>
            <div className="mono" style={{ fontSize: 9, color: C.textMute }}>
              <span style={{ color: C.green }}>●</span> rendered · 2.1s · 78 kb
            </div>
          </div>
          <button style={{ ...iconBtn, background: C.panel, width: 28, height: 28 }}><Icon name="expand" size={12} /></button>
        </div>

        {/* view presets */}
        <div style={{ position: "absolute", top: 50, right: 8, display: "flex", flexDirection: "column", gap: 3, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 4, padding: 2 }}>
          {["TOP", "FRONT", "ISO"].map((l, i) => (
            <div key={l} className="mono" style={{ fontSize: 9, padding: "3px 7px", borderRadius: 2, color: i === 2 ? C.accent : C.textMute, background: i === 2 ? C.accentSoft : "transparent" }}>{l}</div>
          ))}
        </div>

        {/* axes */}
        <div style={{ position: "absolute", left: 8, bottom: sheetTall ? "66%" : "46%", transition: "bottom 180ms" }}>
          <AxesIndicator />
        </div>
      </div>

      {/* bottom sheet */}
      <div style={{
        position: "absolute", left: 0, right: 0, bottom: 0,
        height: sheetTall ? "66%" : "46%",
        background: C.panel, borderTop: `1px solid ${C.line}`,
        borderTopLeftRadius: 12, borderTopRightRadius: 12,
        boxShadow: "0 -18px 30px rgba(0,0,0,0.35)",
        display: "flex", flexDirection: "column",
        transition: "height 180ms",
      }}>
        <button onClick={() => setSheetTall(t => !t)} style={{ background: "transparent", border: "none", padding: "6px 0 4px", display: "flex", justifyContent: "center", cursor: "pointer" }}>
          <div style={{ width: 32, height: 3, borderRadius: 999, background: C.line }} />
        </button>

        {/* presets row */}
        <div style={{ padding: "4px 12px 8px", display: "flex", gap: 5, overflow: "auto", borderBottom: `1px solid ${C.line}` }}>
          {PRESETS.map(p => (
            <div key={p.id} style={{
              flexShrink: 0, fontSize: 10, padding: "4px 9px", borderRadius: 999,
              border: `1px solid ${p.id === "70" ? C.accentLine : C.line}`,
              color: p.id === "70" ? C.accent : C.textDim,
              background: p.id === "70" ? C.accentSoft : "transparent",
              whiteSpace: "nowrap",
            }}>{p.name}</div>
          ))}
          <div style={{ flexShrink: 0, fontSize: 10, padding: "4px 9px", borderRadius: 999, border: `1px dashed ${C.line}`, color: C.textDim }}>+ save</div>
        </div>

        {/* group tabs */}
        <div style={{ padding: "0 6px", display: "flex", gap: 0, borderBottom: `1px solid ${C.line}` }}>
          {PARAM_GROUPS.map(g => (
            <button key={g.id} onClick={() => setGroup(g.id)}
              style={{
                flex: 1, background: "transparent", border: "none",
                color: group === g.id ? C.text : C.textMute,
                fontSize: 11, fontWeight: 600, padding: "8px 0 10px", cursor: "pointer",
                borderBottom: `2px solid ${group === g.id ? C.accent : "transparent"}`,
              }}>
              {g.label}
              <span className="mono" style={{ fontSize: 9, color: C.textMute, marginLeft: 4 }}>{g.params.length}</span>
            </button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: "12px 14px 76px", display: "flex", flexDirection: "column", gap: 14 }}>
          {groupObj.params.map(p => <ParamControlStatic key={p.name} param={p} />)}
        </div>

        {/* CTA */}
        <div style={{ position: "absolute", bottom: 10, left: 10, right: 10 }}>
          <button style={{
            width: "100%", background: C.accent, color: C.accentInk, border: "none", padding: "11px",
            borderRadius: 5, fontSize: 13, fontWeight: 600, cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}>
            <Icon name="download" size={13} stroke={C.accentInk} /> Download STL · 78 kb
          </button>
        </div>
      </div>
    </div>
  );
}

function ParamControlStatic({ param }) {
  if (param.kind === "boolean") {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 12 }}>{param.label}</div>
        <div style={{ width: 32, height: 18, borderRadius: 999, border: `1px solid ${param.value ? C.accentLine : C.line}`, background: param.value ? C.accent : "transparent", position: "relative" }}>
          <div style={{ width: 12, height: 12, borderRadius: 999, background: param.value ? C.accentInk : C.textMute, position: "absolute", top: 2, left: param.value ? 17 : 2 }} />
        </div>
      </div>
    );
  }
  const pct = ((param.value - param.min) / (param.max - param.min)) * 100;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <div style={{ fontSize: 12 }}>{param.label}</div>
        <div className="mono" style={{ fontSize: 11, color: C.accent }}>{param.value}<span style={{ color: C.textMute, marginLeft: 2 }}>{param.unit}</span></div>
      </div>
      <div style={{ position: "relative", height: 20 }}>
        <div style={{ position: "absolute", top: 9, left: 0, right: 0, height: 2, background: C.line }} />
        <div style={{ position: "absolute", top: 9, left: 0, width: `${pct}%`, height: 2, background: C.accent }} />
        <div style={{ position: "absolute", top: 3, left: `calc(${pct}% - 7px)`, width: 14, height: 14, borderRadius: 999, background: C.accent, border: `2px solid ${C.panel}` }} />
      </div>
    </div>
  );
}

Object.assign(window, {
  CaliperHome, CaliperDetail, CaliperPrintPrep, CaliperCmdK,
  CaliperMobile, CaliperMobileStacked: CaliperMobile, CaliperMobileSheet: CaliperMobile,
});
