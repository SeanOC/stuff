// Supplemental artboards — share flow, keyboard shortcut reference,
// preset/param merge behavior, and a responsive breakpoint spec.

function CaliperShareToast({ m, onBack, onOpenCmd }) {
  const url = "https://stuff.xyz/m/cylindrical_holder_slot?d=70&c=0.75&h=35&w=3&a=120&sl=2&sh=75&cd=5&gb=28&gf=10&gd=6&gc=1";
  return (
    <CaliperChrome onBack={onBack} onOpenCmd={onOpenCmd}
      crumbs={<span>~/ library / <span style={{ color: C.text }}>cylindrical_holder_slot.scad</span></span>}>
      <div style={{ flex: 1, position: "relative", background: C.bg }}>
        <ViewerGrid />
        <div style={{ position: "absolute", inset: "12% 22%" }}>
          <HolderGlyph accent={C.accent} muted={C.textMute} />
        </div>
        <div style={{ position: "absolute", inset: 0, background: "rgba(10,12,15,0.55)" }} />
        <div style={{ position: "absolute", left: "50%", top: 80, transform: "translateX(-50%)", width: 520, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 6, boxShadow: "0 20px 60px rgba(0,0,0,0.55)", padding: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Icon name="share" size={14} stroke={C.accent} />
            <span style={{ fontSize: 13, fontWeight: 600 }}>Share these parameters</span>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 10, color: C.textMute }}>snapshot #70-v3</span>
          </div>
          <p style={{ margin: "0 0 12px", fontSize: 12, color: C.textDim, lineHeight: 1.5 }}>
            Anyone with the link sees the exact param set you have now. They can tweak further; the link they copy back will differ.
          </p>
          <div className="mono" style={{ background: C.bg, border: `1px solid ${C.line}`, borderRadius: 4, padding: "8px 10px", fontSize: 11, color: C.textDim, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginBottom: 10 }}>
            {url}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button style={{ flex: 1, background: C.accent, color: C.accentInk, border: "none", padding: "6px 10px", borderRadius: 3, fontSize: 11, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 5 }}>
              <Icon name="copy" size={11} stroke={C.accentInk} /> Copy link
            </button>
            <button style={{ background: "transparent", color: C.textDim, border: `1px solid ${C.line}`, padding: "6px 10px", borderRadius: 3, fontSize: 11, cursor: "pointer" }}>Copy short</button>
            <button style={{ background: "transparent", color: C.textDim, border: `1px solid ${C.line}`, padding: "6px 10px", borderRadius: 3, fontSize: 11, cursor: "pointer" }}>Download .json</button>
          </div>
        </div>
        {/* Success toast */}
        <div style={{ position: "absolute", right: 16, bottom: 16, background: C.panel, border: `1px solid ${C.accentLine}`, borderRadius: 4, padding: "8px 12px", display: "flex", alignItems: "center", gap: 8 }}>
          <Icon name="check" size={12} stroke={C.green} />
          <span style={{ fontSize: 11 }}>Link copied</span>
          <span className="mono" style={{ fontSize: 9, color: C.textMute }}>⌘⇧C</span>
        </div>
      </div>
    </CaliperChrome>
  );
}

function ShortcutSheet({ onBack, onOpenCmd }) {
  const groups = [
    { label: "Global", items: [
      ["⌘ K", "Open command palette"],
      ["⌘ L", "Go to library"],
      ["⌘ ,", "Preferences"],
      ["?",   "Show this sheet"],
    ]},
    { label: "Model", items: [
      ["⌘ E",  "Download STL"],
      ["⌘ ⇧ C", "Copy share link"],
      ["⌘ P",  "Open print prep"],
      ["⌘ /",  "Toggle source view"],
    ]},
    { label: "Viewer", items: [
      ["1 / 2 / 3", "Top / Front / Iso"],
      ["G",   "Toggle grid"],
      ["D",   "Toggle dimensions"],
      ["F",   "Fullscreen viewer"],
      ["R",   "Reset camera"],
    ]},
    { label: "Presets", items: [
      ["⌘ 1–9", "Load preset by index"],
      ["⌘ S",   "Save current as preset"],
    ]},
  ];
  return (
    <CaliperChrome onBack={onBack} onOpenCmd={onOpenCmd} crumbs={<span>~/ <span style={{ color: C.text }}>shortcuts</span></span>}>
      <div style={{ flex: 1, overflow: "auto", padding: "24px 28px 40px", background: C.bg }}>
        <div className="mono" style={{ color: C.textMute, fontSize: 10, letterSpacing: "0.12em" }}>REFERENCE</div>
        <h1 style={{ margin: "6px 0 24px", fontSize: 22, fontWeight: 600 }}>Keyboard shortcuts</h1>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 24 }}>
          {groups.map(g => (
            <div key={g.label} style={{ border: `1px solid ${C.line}`, borderRadius: 4, overflow: "hidden" }}>
              <div style={{ padding: "9px 14px", background: C.panel, borderBottom: `1px solid ${C.line}` }}>
                <div className="mono" style={{ fontSize: 10, letterSpacing: "0.1em", color: C.textMute }}>{g.label.toUpperCase()}</div>
              </div>
              <div>
                {g.items.map(([k, v], i) => (
                  <div key={k} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 14px", borderBottom: i === g.items.length - 1 ? "none" : `1px solid ${C.lineSoft}` }}>
                    <div style={{ fontSize: 12, color: C.text }}>{v}</div>
                    <div style={{ display: "flex", gap: 4 }}>
                      {k.split(" ").map((p, j) => <Kbd key={j}>{p}</Kbd>)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 28, border: `1px solid ${C.line}`, borderRadius: 4, padding: 18, background: C.panel }}>
          <div className="mono" style={{ fontSize: 10, letterSpacing: "0.1em", color: C.textMute }}>BEHAVIOR RULES</div>
          <h2 style={{ margin: "6px 0 14px", fontSize: 15 }}>How presets and parameters interact</h2>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10, fontSize: 12, color: C.textDim, lineHeight: 1.55 }}>
            <li><span className="mono" style={{ color: C.accent, marginRight: 6 }}>01</span> Loading a preset <em>replaces all</em> params with the preset values. No partial merge.</li>
            <li><span className="mono" style={{ color: C.accent, marginRight: 6 }}>02</span> Nudging any slider after a preset is loaded shows a <span style={{ color: C.text }}>modified dot</span> next to the preset name; the preset stays selected but marked <span className="mono" style={{ color: C.warn }}>(modified)</span>.</li>
            <li><span className="mono" style={{ color: C.accent, marginRight: 6 }}>03</span> If a value falls outside the range the preset was designed for, the slider still accepts it — OpenSCAD validates on render, not on input.</li>
            <li><span className="mono" style={{ color: C.accent, marginRight: 6 }}>04</span> A preset's mute/bool fields (e.g. <code style={{ color: C.text }}>gusset_bottom_chamfer</code>) carry semantic intent; loading <span style={{ color: C.text }}>46mm</span> explicitly disables chamfer even though the user may have enabled it manually.</li>
            <li><span className="mono" style={{ color: C.accent, marginRight: 6 }}>05</span> "Save as preset" captures the current param set verbatim. User presets live in localStorage; stock presets are source-declared.</li>
          </ul>
        </div>

        <div style={{ marginTop: 20, border: `1px solid ${C.line}`, borderRadius: 4, padding: 18, background: C.panel }}>
          <div className="mono" style={{ fontSize: 10, letterSpacing: "0.1em", color: C.textMute }}>RESPONSIVE</div>
          <h2 style={{ margin: "6px 0 10px", fontSize: 15 }}>Breakpoints</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
            {[
              ["≥ 1200 px", "Desktop 3-col", "left rail · viewer · param rail"],
              ["720–1199 px", "Tablet 2-col", "viewer on top · param rail collapses to bottom drawer (peek 80 px)"],
              ["< 720 px", "Mobile", "fullscreen viewer · bottom sheet (46% collapsed, 66% expanded)"],
            ].map(([bp, name, note]) => (
              <div key={bp} style={{ border: `1px solid ${C.lineSoft}`, borderRadius: 3, padding: 10 }}>
                <div className="mono" style={{ fontSize: 10, color: C.accent }}>{bp}</div>
                <div style={{ fontSize: 12, marginTop: 3, fontWeight: 500 }}>{name}</div>
                <div style={{ fontSize: 11, color: C.textDim, marginTop: 3, lineHeight: 1.45 }}>{note}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </CaliperChrome>
  );
}

Object.assign(window, { CaliperShareToast, ShortcutSheet });
