# Handoff: Stuff Redesign (Caliper)

## Overview

**Stuff** is a browser front-end for a collection of parametric 3D models (OpenSCAD `.scad` files). Users browse a small library of printable models (Multiboard accessories, toys/replacements, household miscellany), open any model, tweak its parameters with live-preview sliders, and export an `.stl` for printing.

This handoff covers the **Caliper** direction: a dark pro-tool aesthetic with Linear-compact density. It replaces whatever the current Stuff UI looks like with a single focused flow: **library → detail → print prep**, plus supporting states (loading, error, empty, command palette, share).

## About the Design Files

The files in this bundle are **design references created in HTML** — React + inline-JSX prototypes rendered via Babel-standalone. They show the intended look, density, copy, and behavior. **They are not production code to copy directly.** The task is to **recreate these designs in the target codebase's existing environment** (whatever framework Stuff actually uses — likely a React/Next or Vue app — using its established patterns and component library). If Stuff has no existing frontend yet, pick the framework most appropriate for the project and implement there.

When you see inline styles and a single `C` token object, translate those into the codebase's idiomatic approach: CSS variables, Tailwind config, CSS modules, styled-components — whatever matches the app.

## Fidelity

**High-fidelity.** Colors, typography, spacing, copy, iconography, and interaction states are final. The only deliberate placeholders are the 3D viewer content (an SVG glyph stands in for the actual Three.js / OpenSCAD WASM viewer) and the source-code pane contents. Recreate the chrome pixel-faithfully; swap the placeholder viewer for the real renderer.

## Screens / Views

All desktop artboards are **1440 × 860** unless noted. Mobile is **390 × 844**.

### 1. Library (home)
`cal-home` · 1360 × 820

- **Purpose:** Browse all available models, grouped by category; open one to tweak it.
- **Layout:** Top app bar (38 px) · two-column body. Left rail 220 px wide lists categories with counts. Right column scrolls shelves of cards — one shelf per category.
- **Card:** 1 column on mobile, 2 col on tablet, 3 col on desktop. Each card: title, stem filename in mono-small, 2-line blurb, footer row with param count + preset count + STL size. Hover: border brightens from `line` to `accentLine`, background shifts from `panel` to `panelHi`.
- **Top bar contents (left→right):** STUFF wordmark + version tag · breadcrumb · command palette trigger (shows current shortcut `⌘K`) · account dot.

### 2. Model detail (desktop)
`cal-detail` · 1440 × 860

- **Purpose:** Tweak parameters; watch the live render update; export.
- **Layout:** Three columns.
  - **Left rail (240 px):** Presets list (stock + user), source-file quick-jump, render log with timings.
  - **Viewer (flex):** Full-bleed preview with CAD grid overlay, X/Y/Z axes indicator (bottom-left), view-preset tabs (top · front · iso · fullscreen) top-right, stat strip along the bottom (dimensions · triangle count · render time · STL size).
  - **Param rail (360 px):** Grouped parameters (Cradle / Backer / Gussets). Each param: label, unit, numeric input, slider, min/max ticks.
- **State pill** (bottom-right of viewer, visible in mocks only): toggles between `ready / loading / error / empty` to preview those states on one artboard.

### 3. Print prep
`cal-print` · 1440 × 860

- **Purpose:** Lay out on build plate, pick slicer profile, export.
- **Layout:** Viewer on left, right panel with build-plate selector, orientation presets (flat / upright / angled 45°), slicer handoff picker (OrcaSlicer / Bambu Studio / PrusaSlicer / Download STL), estimated time + filament readout.

### 4. Command palette (⌘K)
`cal-cmdk` · 1440 × 860

- **Purpose:** Jump anywhere, run any action, by keyboard.
- **Layout:** Dimmed detail view behind; centered palette 560 px wide, search input on top, grouped results (Models · Actions · Presets · Recent). Results are keyboard-selectable (↑↓ · Enter); footer shows applicable shortcut hints.

### 5. Loading / Error / Empty
`cal-loading` · `cal-error` · `cal-empty` — all detail-view variants.

- **Loading:** Viewer shows render progress bar + compile log streaming in the bottom stat strip. Param rail stays interactive.
- **Error:** Viewer shows the last good render dimmed; an error strip slides in over the stat bar with the first compiler error, line number, and a "view full log" action.
- **Empty / idle:** Before first render of a fresh model — blank viewer with a small "Press ⏎ to render" hint and disabled export button.

### 6. Mobile detail
`cal-mobile` · 390 × 844

- **Purpose:** Detail view on a phone.
- **Layout:** Fullscreen viewer fills the screen; a bottom sheet peeks at 46% viewport height (collapsed) and expands to 66% (expanded). Handle-to-drag at top. Sheet contents mirror the desktop param rail but one group at a time, with a horizontal chip switcher for groups.

### 7. Share
`cal-share` · 1440 × 860

- **Purpose:** Copy a permalink to the current param set.
- **Layout:** Modal dialog over the detail view. Shows truncated URL, "Copy link" (primary) / "Copy short" / "Download .json" buttons. Success toast (bottom-right, 180 ms slide-up) confirms with `⌘⇧C` shortcut hint.

### 8. Shortcuts + behavior + breakpoints reference
`cal-shortcuts` · 1440 × 1080

- **Purpose:** Single source of truth for keyboard map, preset/param merge rules, and responsive breakpoints.
- Developers should treat this artboard as **authoritative spec** — if anything else in the design contradicts it, the shortcut sheet wins.

## Interactions & Behavior

### Navigation
- Clicking a card in the library opens that model's detail view in place (client-side route change; URL is `/m/<slug>` — e.g. `/m/cylindrical_holder_slot`).
- `⌘K` opens the command palette from anywhere.
- Back button in the top bar returns to the library.

### Parameter editing
- Sliders and number inputs are bound to the same value; dragging the slider updates the number immediately, and vice versa.
- Values outside a slider's declared min/max are still accepted via direct typing — OpenSCAD validates on render, not on input.
- A **modified dot** appears next to the preset name when any value differs from the selected preset. The preset stays selected but is labeled `(modified)` in mono.
- **Render strategy:** Debounce param changes (250 ms) and kick a render. Cancel in-flight renders when a new one starts.

### Presets
- Loading a preset **replaces all** params with the preset values. No partial merge.
- A preset's boolean/mute fields carry semantic intent (e.g. loading `46mm can` explicitly disables `gusset_bottom_chamfer` even if the user had it on).
- "Save as preset" captures the current set verbatim. User presets persist to `localStorage` under `stuff.presets.<modelSlug>`. Stock presets are declared in source.
- `⌘1`–`⌘9` load presets 1–9 by index.

### Share
- `⌘⇧C` copies a permalink. URL format: `stuff.xyz/m/<slug>?<key>=<value>&...` with short keys matching the param's short-code (e.g. `d` = diameter, `c` = clearance). See `cal-share` artboard for an example.
- "Copy short" copies a shortened URL via a url-shortener (the app does not own — punt to `tinyurl`-class service or a backend endpoint if Stuff has one).
- "Download .json" writes the param set as `<slug>-params.json`.
- Success toast auto-dismisses after 2 s.

### View controls
- Number keys `1` / `2` / `3` snap the camera to top / front / iso.
- `G` toggles the grid, `D` toggles dimension labels, `R` resets the camera, `F` enters fullscreen viewer.

### Print prep
- Slicer handoff uses the slicer's URL-scheme where available (e.g. `orcaslicer://open?url=…`). Fallback: download the STL.
- Estimated time + filament are placeholders — the real calc depends on the slicer and is out of scope for the first pass.

## State Management

Minimal. Per-model detail view:

```ts
type DetailState = {
  modelSlug: string;
  params: Record<string, number | boolean | string>;
  activePresetId: string | null;
  modifiedSincePreset: boolean;
  renderState: 'idle' | 'loading' | 'ready' | 'error';
  renderResult: { stlUrl: string; triCount: number; ms: number } | null;
  renderError: { line: number; message: string; log: string } | null;
  camera: 'top' | 'front' | 'iso';
  showGrid: boolean;
  showDims: boolean;
};
```

Global: `cmdkOpen: boolean`, `currentRoute`, `userPresets: Record<modelSlug, Preset[]>`.

Persist to `localStorage`:
- `stuff.presets.<slug>` — user presets per model
- `stuff.lastParams.<slug>` — last-edited params per model (so reopening restores)
- `stuff.prefs` — grid/dim visibility, preferred camera, preferred slicer

## Design Tokens

**Caliper palette** (the single source of truth — copy these into your theme):

```ts
const caliper = {
  bg:         '#0c0d10',  // app background
  panel:      '#131418',  // top bar, left rail, cards
  panel2:     '#181a1f',  // input backgrounds, nested panels
  panelHi:    '#1d1f25',  // card hover, active preset
  line:       '#22252c',  // 1 px dividers and borders
  lineSoft:   '#1a1c21',  // within-card dividers
  text:       '#e7e2d6',  // primary ink
  textDim:    '#8a8578',  // secondary ink
  textMute:   '#555147',  // tertiary / tick marks
  accent:     '#e7e2d6',  // warm off-white signal (same as text — used against panel)
  accentInk:  '#0c0d10',  // ink on accent backgrounds
  accentSoft: '#e7e2d614',// 8% tint of accent
  accentLine: '#e7e2d644',// 27% tint for focus rings
  red:        '#d96a6a',  // error
  green:      '#8ee29d',  // success / render ok
  blue:       '#7ab6ff',  // info
  warn:       '#f0c06a',  // modified / warn
};
```

**Typography**
- Sans: **IBM Plex Sans**, 400 / 500 / 600.
- Mono: **IBM Plex Mono**, 400 / 500. Used for filenames, shortcut keys, numeric ticks, and stat-strip values.
- Scale in px: `10 / 11 / 12 / 13 / 14 / 15 / 22`. 13 is the default body size; 11 is the top bar; 10 is for mono labels. No text below 10 px.
- Letter-spacing: `0.08em` for the STUFF wordmark, `0.1em–0.12em` for all-caps mono labels. Body uses default.
- Line-height: `1.45` for paragraphs, `1.55` for the behavior list on the shortcut sheet. UI chrome uses the default.

**Spacing scale** (px): `2 / 3 / 4 / 6 / 8 / 10 / 12 / 14 / 18 / 24 / 28 / 40`. Prefer the smaller values — Caliper is dense by design.

**Radius:** `3` (default for inline elements: kbd, pills, inputs) · `4` (buttons, cards, inputs) · `6` (dialogs only).

**Border:** always 1 px. Inside a panel, use `lineSoft`; on the outer surface of a panel, use `line`.

**Shadows:** only on modals — `0 20px 60px rgba(0,0,0,0.55)`. Cards do not use shadow; use border + background shift for elevation.

**Chrome heights:**
- Top bar: 38 px
- Stat strip (viewer bottom): 36 px
- Kbd pill: 18 px high, 5 px horizontal padding

## Responsive

Three breakpoints. See `cal-shortcuts` artboard for the authoritative version:

- **≥ 1200 px — Desktop 3-col:** left rail · viewer · param rail
- **720–1199 px — Tablet 2-col:** viewer on top · param rail collapses to bottom drawer (peek 80 px)
- **< 720 px — Mobile:** fullscreen viewer · bottom sheet (46% collapsed, 66% expanded)

## Keyboard Shortcuts (authoritative)

Also rendered on `cal-shortcuts`.

**Global**
- `⌘ K` — command palette · `⌘ L` — library · `⌘ ,` — preferences · `?` — shortcut sheet

**Model**
- `⌘ E` — download STL · `⌘ ⇧ C` — copy share link · `⌘ P` — print prep · `⌘ /` — toggle source view

**Viewer**
- `1 / 2 / 3` — top / front / iso · `G` — grid · `D` — dims · `F` — fullscreen · `R` — reset camera

**Presets**
- `⌘ 1`–`⌘ 9` — load preset by index · `⌘ S` — save current as preset

## Assets

- **Fonts:** IBM Plex Sans + IBM Plex Mono (Google Fonts). No proprietary fonts.
- **Icons:** Small custom stroke set inlined as SVG in `shared.jsx`'s `<Icon>` component. When reimplementing, substitute **Lucide** (or whatever the codebase already uses) with stroke-width 1.5 and the same size (12–14 px). Names used: `arrow-left`, `copy`, `share`, `check`, `search`, `download`, `play`, `grid`, `layers`, `maximize`.
- **3D viewer placeholder:** The SVG `HolderGlyph` in `shared.jsx` stands in for the real viewer. Replace with the actual render engine (presumably Three.js bound to the OpenSCAD WASM output Stuff already generates).

## Model Data

See the `MODELS`, `MODEL_CATEGORIES`, and `PARAM_GROUPS` exports in `shared.jsx` for the exact strings used in the mocks. Treat those as placeholder data — the real app already has the model catalogue; feed that in instead.

## Files

All files are in this bundle's `/design_files/` directory. To view the running prototype, open `Stuff Redesign.html` in a browser. Reference screenshots of every artboard are in `/screenshots/`.

### Screenshots
- `screenshots/01-library-desktop.png`
- `screenshots/02-detail-desktop.png`
- `screenshots/03-print-prep.png`
- `screenshots/04-command-palette.png`
- `screenshots/05-state-loading.png`
- `screenshots/06-state-error.png`
- `screenshots/07-state-empty.png`
- `screenshots/08-mobile-detail.png`
- `screenshots/09-share-dialog.png`
- `screenshots/10-shortcuts-reference.png`

### Source files

- `Stuff Redesign.html` — entry point; pulls React, ReactDOM, Babel-standalone, and the JSX files below.
- `main.jsx` — `<App>` composition; wires the artboards into the design canvas.
- `shared.jsx` — model data, param groups, icon set, 3D placeholder glyph.
- `caliper.jsx` — all Caliper screens: chrome, library, detail, print prep, cmdk, mobile, and state variants.
- `share-and-shortcuts.jsx` — share dialog + toast, and the shortcut/behavior/breakpoint reference artboard.
- `design-canvas.jsx` — presentation shell that lays the artboards out; not part of the product.

## Open Questions for Implementation

A short list of things the design does **not** decide; the developer should resolve with product:

1. **URL short-key mapping.** The share URL uses abbreviated keys (`d` = diameter, `c` = clearance, …). The full map lives implicitly in the share artboard; formalize it as a `shortKey → paramName` lookup per model in source and make it stable across versions.
2. **Slicer deep-link schemes.** Which slicers to actually wire up. OrcaSlicer, Bambu Studio, and PrusaSlicer all accept URL schemes; the list shown is my guess.
3. **Renderer backend.** Whether the OpenSCAD compile runs client-side (WASM) or server-side (queue + CDN cached STLs). The error-state design assumes compile errors return a line number; confirm that matches the actual pipeline.
4. **Auth.** Top bar shows an account dot; no auth flow is designed. Presets persist to `localStorage` today; if they should sync across devices, that's new scope.
