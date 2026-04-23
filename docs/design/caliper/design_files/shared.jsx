// Shared data + mini icon set used by both design directions.

const MODELS = {
  multiboard: [
    {
      slug: "cylindrical_holder_slot",
      title: "Cylindrical Holder — Slot",
      stem: "cylindrical_holder_slot.scad",
      blurb: "Multiboard-mounted holder for any cylindrical item. 42–77mm tested.",
      paramCount: 11,
      presets: ["42mm can", "46mm can", "70mm spray", "77mm spray"],
      size: "120 × 80 × 48 mm",
      lastRender: "2.1 s",
      stl: "78 kb",
    },
    {
      slug: "multiboard_tray",
      title: "Parts Tray",
      stem: "multiboard_tray.scad",
      blurb: "Shallow tray with dividers. Clips onto any Multiboard grid.",
      paramCount: 7,
      presets: ["2×2", "3×2", "4×3"],
      size: "100 × 75 × 22 mm",
      lastRender: "1.4 s",
      stl: "41 kb",
    },
    {
      slug: "hex_peg_hook",
      title: "Hex Peg Hook",
      stem: "hex_peg_hook.scad",
      blurb: "Single hook with optional hex backing pattern and rubber tip.",
      paramCount: 5,
      presets: ["Short", "Tall", "L-bend"],
      size: "45 × 28 × 60 mm",
      lastRender: "0.9 s",
      stl: "22 kb",
    },
  ],
  toys: [
    {
      slug: "popcorn_kernel",
      title: "Popcorn Kernel",
      stem: "popcorn_kernel.scad",
      blurb: "Replacement piece for a Disney toddler toy. Solid sphere union.",
      paramCount: 4,
      presets: ["Small", "Standard"],
      size: "28 × 26 × 22 mm",
      lastRender: "0.6 s",
      stl: "14 kb",
    },
    {
      slug: "marble_run_piece",
      title: "Marble Run — Curve",
      stem: "marble_run_piece.scad",
      blurb: "Parametric curved track with configurable bend radius.",
      paramCount: 6,
      presets: ["Tight", "Wide", "S-curve"],
      size: "140 × 60 × 30 mm",
      lastRender: "1.8 s",
      stl: "63 kb",
    },
  ],
  misc: [
    {
      slug: "cable_clip",
      title: "Desk Cable Clip",
      stem: "cable_clip.scad",
      blurb: "Stick-on clip for 1–4 cables. Parametric channel count.",
      paramCount: 3,
      presets: ["1-way", "2-way", "4-way"],
      size: "38 × 22 × 14 mm",
      lastRender: "0.4 s",
      stl: "8 kb",
    },
    {
      slug: "threaded_knob",
      title: "Threaded Knob",
      stem: "threaded_knob.scad",
      blurb: "M3–M10 knob with knurled grip, threaded insert pocket.",
      paramCount: 6,
      presets: ["M3", "M5", "M8"],
      size: "32 × 32 × 18 mm",
      lastRender: "1.1 s",
      stl: "29 kb",
    },
    {
      slug: "stacking_bin",
      title: "Stacking Bin",
      stem: "stacking_bin.scad",
      blurb: "Chamfered open-top bin that nests with its own kind.",
      paramCount: 8,
      presets: ["Small", "Medium", "Large"],
      size: "80 × 60 × 40 mm",
      lastRender: "1.3 s",
      stl: "55 kb",
    },
  ],
};

const MODEL_CATEGORIES = [
  { id: "multiboard", label: "Multiboard", count: MODELS.multiboard.length, note: "Accessories for Multiboard grid systems." },
  { id: "toys", label: "Toys & Replacements", count: MODELS.toys.length, note: "One-off replacements and tinkering pieces." },
  { id: "misc", label: "Household & Misc", count: MODELS.misc.length, note: "Everything else that earns its print time." },
];

// Parameter groups for the detail screen. Uses cylindrical_holder_slot.scad as
// the reference model — faithful to the real @param set.
const PARAM_GROUPS = [
  {
    id: "cradle",
    label: "Cradle",
    params: [
      { name: "can_diameter", label: "Item diameter", unit: "mm", kind: "number", min: 20, max: 200, step: 0.5, value: 70 },
      { name: "clearance", label: "Slip clearance", unit: "mm", kind: "number", min: 0, max: 2, step: 0.05, value: 0.75 },
      { name: "ring_height", label: "Ring height", unit: "mm", kind: "number", min: 5, max: 200, step: 1, value: 35 },
      { name: "wall", label: "Wall thickness", unit: "mm", kind: "number", min: 1, max: 10, step: 0.5, value: 3 },
      { name: "front_opening_deg", label: "Front opening arc", unit: "°", kind: "number", min: 0, max: 270, step: 5, value: 120 },
    ],
  },
  {
    id: "backer",
    label: "Backer",
    params: [
      { name: "slot_count", label: "Slot count", unit: "", kind: "integer", min: 1, max: 6, step: 1, value: 2 },
      { name: "slot_region_height", label: "Slot region height", unit: "mm", kind: "number", min: 25, max: 150, step: 5, value: 75 },
      { name: "cup_depth", label: "Drip-cup depth", unit: "mm", kind: "number", min: 0, max: 30, step: 0.5, value: 5 },
    ],
  },
  {
    id: "gusset",
    label: "Gusset",
    params: [
      { name: "gusset_back_w", label: "Back width", unit: "mm", kind: "number", min: 5, max: 60, step: 1, value: 28 },
      { name: "gusset_front_w", label: "Front width", unit: "mm", kind: "number", min: 2, max: 40, step: 1, value: 10 },
      { name: "gusset_depth", label: "Depth", unit: "mm", kind: "number", min: 2, max: 20, step: 0.5, value: 6 },
      { name: "gusset_bottom_chamfer", label: "Chamfer bottom edge", unit: "", kind: "boolean", value: true },
    ],
  },
];

const PRESETS = [
  { id: "42", name: "42mm can", sub: "soda / slim", active: false },
  { id: "46", name: "46mm can", sub: "standard — bed adhesion tweak", active: false },
  { id: "70", name: "70mm spraycan", sub: "WD-40 class", active: true },
  { id: "77", name: "77mm spraycan", sub: "full-size rattle can", active: false },
];

const MODEL_NOTES = [
  "Consolidates four earlier fixed-diameter variants into one @param-driven source.",
  "46mm preset disables the bottom chamfer intentionally — trade corner strength for bed adhesion.",
  "Manifold backend required. CGAL OOMs on BOSL2.",
];

// Simple inline icons (stroke-based). Size via width/height on usage.
function Icon({ name, size = 16, stroke = "currentColor", strokeWidth = 1.6, fill = "none", style }) {
  const common = { width: size, height: size, viewBox: "0 0 24 24", fill, stroke, strokeWidth, strokeLinecap: "round", strokeLinejoin: "round", style };
  switch (name) {
    case "download": return <svg {...common}><path d="M12 3v12m0 0l-4-4m4 4l4-4" /><path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" /></svg>;
    case "cube": return <svg {...common}><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z" /><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5" /></svg>;
    case "search": return <svg {...common}><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>;
    case "settings": return <svg {...common}><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 00-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 00-2-1.2L14 3h-4l-.6 2.6a7 7 0 00-2 1.2L5 6l-2 3.4 2 1.5a7 7 0 000 2.2l-2 1.5 2 3.4 2.3-.9a7 7 0 002 1.2L10 21h4l.6-2.6a7 7 0 002-1.2l2.3.9 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z" /></svg>;
    case "chevron-down": return <svg {...common}><path d="M6 9l6 6 6-6" /></svg>;
    case "chevron-right": return <svg {...common}><path d="M9 6l6 6-6 6" /></svg>;
    case "chevron-left": return <svg {...common}><path d="M15 6l-6 6 6 6" /></svg>;
    case "arrow-left": return <svg {...common}><path d="M20 12H4m0 0l6-6m-6 6l6 6" /></svg>;
    case "expand": return <svg {...common}><path d="M4 10V4h6M20 10V4h-6M4 14v6h6M20 14v6h-6" /></svg>;
    case "axes": return <svg {...common}><path d="M4 20L20 4" /><path d="M4 20h6M4 20v-6" /><path d="M20 4l-3 3M20 4v5M20 4h-5" /></svg>;
    case "plus": return <svg {...common}><path d="M12 5v14M5 12h14" /></svg>;
    case "minus": return <svg {...common}><path d="M5 12h14" /></svg>;
    case "check": return <svg {...common}><path d="M5 12l4 4 10-10" /></svg>;
    case "star": return <svg {...common}><path d="M12 3l2.7 5.5 6 .9-4.4 4.2 1 6-5.4-2.8-5.4 2.8 1-6-4.3-4.2 6-.9L12 3z" /></svg>;
    case "clock": return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>;
    case "filament": return <svg {...common}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /></svg>;
    case "share": return <svg {...common}><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8.2 10.8l7.6-4M8.2 13.2l7.6 4" /></svg>;
    case "copy": return <svg {...common}><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V6a2 2 0 00-2-2H6a2 2 0 00-2 2v8a2 2 0 002 2h2" /></svg>;
    case "grid": return <svg {...common}><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></svg>;
    case "list": return <svg {...common}><path d="M4 6h16M4 12h16M4 18h16" /></svg>;
    case "menu": return <svg {...common}><path d="M4 7h16M4 12h16M4 17h16" /></svg>;
    case "x": return <svg {...common}><path d="M6 6l12 12M18 6L6 18" /></svg>;
    case "slider": return <svg {...common}><path d="M4 8h10M18 8h2" /><circle cx="16" cy="8" r="2" /><path d="M4 16h4M12 16h8" /><circle cx="10" cy="16" r="2" /></svg>;
    case "eye": return <svg {...common}><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" /><circle cx="12" cy="12" r="3" /></svg>;
    case "info": return <svg {...common}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.1" /></svg>;
    default: return null;
  }
}

// A fake 3d-ish illustration of the cylindrical holder, used as a stable
// placeholder across thumbnails + previews. Pure SVG, no external deps.
function HolderGlyph({ accent = "currentColor", muted = "currentColor", bg = "transparent", style, showRule = false }) {
  return (
    <svg viewBox="0 0 240 180" style={{ display: "block", width: "100%", height: "100%", ...style }}>
      <rect width="240" height="180" fill={bg} />
      {/* Backer (flat rectangle) */}
      <g opacity="0.9">
        <path d="M70 30 L170 30 L170 150 L70 150 Z" fill="none" stroke={muted} strokeWidth="1.2" />
        {/* slot mouths */}
        <rect x="100" y="50" width="40" height="6" fill="none" stroke={muted} strokeWidth="1" />
        <rect x="100" y="75" width="40" height="6" fill="none" stroke={muted} strokeWidth="1" />
        <rect x="100" y="100" width="40" height="6" fill="none" stroke={muted} strokeWidth="1" />
      </g>
      {/* Cradle (ellipse + rim) */}
      <g>
        <ellipse cx="120" cy="155" rx="55" ry="10" fill="none" stroke={accent} strokeWidth="1.4" />
        <ellipse cx="120" cy="85" rx="55" ry="10" fill="none" stroke={accent} strokeWidth="1.4" />
        <path d="M65 85 L65 155" stroke={accent} strokeWidth="1.4" />
        <path d="M175 85 L175 155" stroke={accent} strokeWidth="1.4" />
        {/* front opening cut */}
        <path d="M90 88 A55 10 0 0 0 150 88" stroke={bg === "transparent" ? accent : bg} strokeWidth="3" fill="none" />
      </g>
      {/* Gusset */}
      <path d="M120 85 L140 30 L100 30 Z" fill="none" stroke={muted} strokeWidth="1" opacity="0.6" />
      {showRule && (
        <g fontSize="8" fill={muted} fontFamily="IBM Plex Mono, monospace">
          <line x1="65" y1="170" x2="175" y2="170" stroke={muted} strokeWidth="0.5" />
          <line x1="65" y1="166" x2="65" y2="174" stroke={muted} strokeWidth="0.5" />
          <line x1="175" y1="166" x2="175" y2="174" stroke={muted} strokeWidth="0.5" />
          <text x="120" y="178" textAnchor="middle">110 mm</text>
        </g>
      )}
    </svg>
  );
}

// Generic glyph per model type (very simple — placeholder vibes).
function ModelGlyph({ slug, accent, muted, bg = "transparent" }) {
  const common = { viewBox: "0 0 120 90", style: { display: "block", width: "100%", height: "100%" } };
  if (slug === "popcorn_kernel") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <circle cx="50" cy="40" r="14" />
          <circle cx="68" cy="38" r="12" />
          <circle cx="58" cy="54" r="11" />
          <circle cx="72" cy="54" r="9" />
          <path d="M38 65 L85 65" stroke={muted} />
        </g>
      </svg>
    );
  }
  if (slug === "multiboard_tray") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <rect x="22" y="22" width="76" height="50" />
          <path d="M48 22 L48 72 M74 22 L74 72 M22 45 L98 45" stroke={muted} />
        </g>
      </svg>
    );
  }
  if (slug === "hex_peg_hook") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <polygon points="35,20 55,20 65,37 55,54 35,54 25,37" />
          <path d="M55 37 Q75 37 75 60 L80 60" />
        </g>
      </svg>
    );
  }
  if (slug === "marble_run_piece") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <path d="M20 30 Q60 10 100 30 L100 60 Q60 40 20 60 Z" />
          <circle cx="40" cy="38" r="4" fill={accent} stroke="none" />
        </g>
      </svg>
    );
  }
  if (slug === "cable_clip") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <path d="M25 60 L25 35 Q25 25 40 25 L80 25 Q95 25 95 35 L95 60" />
          <circle cx="45" cy="35" r="4" stroke={muted} />
          <circle cx="60" cy="35" r="4" stroke={muted} />
          <circle cx="75" cy="35" r="4" stroke={muted} />
        </g>
      </svg>
    );
  }
  if (slug === "threaded_knob") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <circle cx="60" cy="45" r="22" />
          <circle cx="60" cy="45" r="8" stroke={muted} />
          {[...Array(12)].map((_, i) => {
            const a = (i / 12) * Math.PI * 2;
            const x1 = 60 + Math.cos(a) * 22;
            const y1 = 45 + Math.sin(a) * 22;
            const x2 = 60 + Math.cos(a) * 27;
            const y2 = 45 + Math.sin(a) * 27;
            return <path key={i} d={`M${x1} ${y1} L${x2} ${y2}`} stroke={muted} />;
          })}
        </g>
      </svg>
    );
  }
  if (slug === "stacking_bin") {
    return (
      <svg {...common}>
        <rect width="120" height="90" fill={bg} />
        <g fill="none" stroke={accent} strokeWidth="1.2">
          <path d="M25 25 L95 25 L85 70 L35 70 Z" />
          <path d="M35 25 L45 70 M85 25 L75 70" stroke={muted} />
        </g>
      </svg>
    );
  }
  // Default to holder glyph
  return <HolderGlyph accent={accent} muted={muted} bg={bg} />;
}

Object.assign(window, { MODELS, MODEL_CATEGORIES, PARAM_GROUPS, PRESETS, MODEL_NOTES, Icon, HolderGlyph, ModelGlyph });
