---
title: Caliper Redesign Phase 1 — Library + Detail Chrome + Viewer + Param Rail
type: feat
date: 2026-04-22
epic: st-gtb
phase: 1
revised: 2026-04-23 (post plan-review synthesis: DHH, Kieran-TS, code-simplicity)
---

# Caliper Redesign Phase 1 — Library + Detail Chrome + Viewer + Param Rail

Phase 0 (bead `st-586`, commit `bc1b477`) landed Tailwind v4 `@theme` tokens in `app/globals.css`, IBM Plex fonts, and `components/AppShell.tsx` (38 px top bar, 220 px left rail on ≥ 1200 px). Phase 1 replaces the gallery with a categorized library, replaces `components/ModelStudio.tsx` with a 3-column detail page, wraps `components/StlViewer.tsx` with Caliper chrome, and rebuilds `components/ParamForm.tsx` as a grouped rail of slider-bound rows.

Design fidelity: pixel-faithful to `docs/design/caliper/screenshots/01-library-desktop.png` and `02-detail-desktop.png`. The JSX references under `docs/design/caliper/design_files/` are composition hints only; do not copy verbatim.

## Three beads

```
Phase 0 (shipped)
       │
       ├── 1.a Library page + catalog + categories        (independent)
       │
       └── 1.b Detail shell + useRenderer + param metadata (backbone)
                    │
                    └── 1.c Detail chrome: viewer + param rail
```

1.a and 1.b can run in parallel on two polecats. 1.c depends on 1.b.

## Architectural decisions

### D1. State — `useDetailState` hook

One hook at `hooks/useDetailState.ts` owned by `DetailPage`:

```ts
type DetailState = {
  params: Record<string, ParamValue>;
  camera: 'top' | 'front' | 'iso';
  showGrid: boolean;
  showDims: boolean;
};
type ParamValue = number | boolean | string;
```

No preset fields in phase 1 — phase 3 adds them. No context — prop drilling is shallow (DetailPage → 3 children). The hook owns mutator functions (`setParam`, `setCamera`, `toggleGrid`, `toggleDims`) so consumers don't see setters as a bag.

### D2. Render pipeline — `useRenderer` hook

```ts
// hooks/useRenderer.ts
type RenderState =
  | { kind: 'idle' }
  | { kind: 'loading'; since: number }
  | { kind: 'ready'; result: RenderResult }
  | { kind: 'error'; error: RenderError };

type RenderResult = { stlBytes: Uint8Array; triCount: number; ms: number };
type RenderError = { line: number | null; message: string; log: string };

function useRenderer(input: { modelPath: string; source: string; params: Record<string, ParamValue> }): {
  state: RenderState;
  history: RenderResult[];      // ring buffer of last 5 successful renders, for PresetRail log
  refresh: () => void;          // phase 2 will use after fixing a compile error
};
```

- Discriminated union: consumers narrow via `switch (state.kind)`. Impossible to read `result` while `kind === 'loading'`.
- `line: number | null` on `RenderError` — phase 1 always `null`; phase 2 parses.
- Logic ports verbatim from `ModelStudio.tsx` lines 25–66 (250 ms debounce, `renderToken` cancel, `applyParamOverrides` SCAD rewrite). This bead moves; does not change semantics.
- STL size at call sites: `stlBytes.byteLength` — no redundant `sizeBytes` field.

### D3. `<ParamRow>` — one component, internal switch

A single `components/ParamRow.tsx` switches on `param.kind` internally. Number rows show label · unit · `<input type="number" id="param-<name>">` · slider · min/max ticks. Both inputs controlled; both call `onChange(name, value)`. Typing accepts out-of-range (OpenSCAD validates on render). Boolean → pill toggle. Enum → styled `<select>`.

If the switch body exceeds ~80 lines, extract `NumberRow` / `BooleanRow` / `EnumRow` as unexported sub-components in the same file with a `satisfies never` exhaustiveness check.

### D4. Component composition

```
app/models/[slug]/page.tsx  (server) — loadModel(slug) → <DetailPage model=…/>
  components/DetailPage.tsx (client) — owns useDetailState + useRenderer
    ├── <DetailLeftRail/>  240 px — source-file quick-jump, render log from history
    ├── <ViewerChrome/>    flex   — wraps <StlViewer>, adds grid/axes/tabs/stat strip
    └── <ParamRail/>       360 px — grouped <ParamRow>s
```

Server `page.tsx` shrinks to a thin loader. Warnings (currently rendered inline at `app/models/[slug]/page.tsx:34–38`) flow into the left-rail render log as dim-colored entries.

### D5. Library data — `lib/models/catalog.ts`

```ts
export const MODEL_CATEGORIES = [
  { id: 'storage',     label: 'Storage' },
  { id: 'multiboard',  label: 'Multiboard' },
  { id: 'toys',        label: 'Toys' },
] as const;

export const CATALOG: Record<string, { categoryId: string; blurb: string }> = {
  cylindrical_holder_slot:    { categoryId: 'multiboard', blurb: '…' },
  popcorn_kernel:             { categoryId: 'toys',       blurb: '…' },
  spraycan_carrier_6x50mm:    { categoryId: 'storage',    blurb: '…' },
};
```

`listModels()` joins on stem; missing entries throw (no silent `'misc'` fallback). `ModelEntry` gains `categoryId` and `blurb` only — no `presetCount`, no `stlSize` until phase 3 needs them.

### D6. Param metadata — `ParamBase` + `@param` parser extension

Refactor `lib/scad-params/parse.ts` line 48:

```ts
interface ParamBase { name: string; label?: string; group?: string; unit?: string; }
interface NumberParam  extends ParamBase { kind: 'number';  default: number; min?: number; max?: number; step?: number; }
interface BooleanParam extends ParamBase { kind: 'boolean'; default: boolean; }
interface StringParam  extends ParamBase { kind: 'string';  default: string; }
interface EnumParam    extends ParamBase { kind: 'enum';    default: string; choices: string[]; }
type Param = NumberParam | BooleanParam | StringParam | EnumParam;
```

Parser recognizes `unit=mm` and `group=cradle` as free-form tokens on any `@param` line. Annotate all three current `.scad` models with `unit=` and `group=` on every param. Params without `group` land in an "Ungrouped" bucket; group display order is first-occurrence order within each `.scad`.

## Bead 1.a — Library + catalog + categories

**Changes:**
- Add `clsx` dependency. Import directly (`import clsx from "clsx"`). No `lib/cn.ts`.
- Create `lib/models/catalog.ts` with `MODEL_CATEGORIES` and `CATALOG`. Seed all three stems.
- `lib/models/discover.ts` lines 15–28: add `categoryId: string` and `blurb: string` to `ModelEntry`. `listModels()` joins on `CATALOG` — throws on missing stem.
- `lib/models/discover.test.ts`: one new case covering `categoryId`/`blurb` propagation.
- Rewrite `app/page.tsx` per `screenshots/01-library-desktop.png`:
  - Left `<aside>` (rendered directly in the route, not via AppShell): categories list with counts, hover `panel → panelHi`, active `bg-accent-soft`. Width `w-220`.
  - Right column: one shelf per category (`h3` in `text-11 uppercase tracking-wide text-text-dim`), `grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-14`.
  - Card: `rounded-4 border border-line bg-panel hover:border-accent-line hover:bg-panel-hi`. Title `text-13 font-semibold`. Stem `font-mono text-10 text-text-mute`. Blurb with `line-clamp-2`. Footer `font-mono text-10 text-text-mute` shows `N params` only.
- `tests/e2e/gallery.spec.ts`: heading assertion at line 13 updates. Slug/URL assertions at 7–12 stay green.

**Acceptance:** vitest green (≥ 1 new test). E2E green post-heading update. Zero inline styles. At ≥ 1200 px: 3-col card grid, 220 px rail.

## Bead 1.b — Detail shell + useRenderer + param metadata

**Changes:**

1. **Parser extension** — `lib/scad-params/parse.ts`: `ParamBase` interface (D6), optional `unit` and `group` on base. Parse `unit=…` and `group=…` tokens. Tests in `lib/scad-params/parse.test.ts` for: `unit` only, `group` only, both absent, both present.
2. **Annotate `.scad` models** — add `unit=` and `group=` to every `@param` in `cylindrical_holder_slot.scad`, `popcorn_kernel.scad`, `spraycan_carrier_6x50mm.scad`. Natural per-model groupings.
3. **`hooks/useRenderer.ts`** — port `ModelStudio.tsx` lines 25–66 into the hook per D2. Return `{ state, history, refresh }`. Ring buffer of 5 successes for `history`.
4. **`hooks/useRenderer.test.ts`** — one smoke unit test: a newer render's result always wins against an earlier stale render via the token-cancel path. (E2E is too slow to debug this subtle bug.)
5. **`hooks/useDetailState.ts`** — owns `{ params, camera, showGrid, showDims }` + mutators per D1.
6. **`components/DetailPage.tsx`** (client) — composes placeholder `<DetailLeftRail>` (source quick-jump + render log from `history`), placeholder `<ViewerChrome>` (wraps `<StlViewer>` unchanged), placeholder `<ParamRail>` (wraps existing `<ParamForm>` minimally restyled for dark palette). Real chrome in 1.c.
7. **Server shell** — `app/models/[slug]/page.tsx`: load model, render `<DetailPage model={model} />`. Delete inline header/warnings chrome at lines 24–48.
8. **Delete `components/ModelStudio.tsx`** at end of bead.
9. **E2E** — update `tests/e2e/model-page.spec.ts:24` and `tests/e2e/live-preview.spec.ts:10` regexes to match new render log format (proposed: `/\d+ms · [\d.]+kb/`). Keep `#param-base_cut` and "Download STL" literal.

**Acceptance:** all E2E green with the one regex update. `ModelStudio.tsx` deleted. `canvas.__stlViewer` handle still exposed (`StlViewer.tsx:95` untouched). `useRenderer` smoke test passes stale-token scenario.

## Bead 1.c — Detail chrome: viewer + param rail

Depends on 1.b landing.

**Changes (Viewer chrome):**

- Expand `<ViewerChrome>` per `screenshots/02-detail-desktop.png`:
  - CAD grid overlay — inline SVG `<pattern>`, `absolute pointer-events-none`, toggles on `showGrid`.
  - X/Y/Z axes indicator — bottom-left inline SVG, rotates with `camera`.
  - View-preset tabs — top-right, pills for `top / front / iso / fullscreen` in `font-mono text-10 uppercase`. Active pill `bg-accent-soft border-accent-line`. Fullscreen uses the Fullscreen API.
  - 36 px stat strip — bottom, `font-mono text-10`, `h-36 border-t border-line bg-panel flex items-center px-12 gap-18`. Fields: tri count, render ms, STL size (`stlBytes.byteLength` kb). No dimensions (phase 2 adds when bbox is computed).
- `<StlViewer>` gains a `setCameraPreset(preset)` method on the `__stlViewer` debug handle at `StlViewer.tsx:95`. Not replacing the handle — extending it.
- Viewer-scoped keyboard via `onKeyDown` on the `<section tabIndex={0}>`: `1/2/3` → camera; `G` → grid; `D` → dims; `F` → fullscreen. No `R` reset — defer to phase 3 global map.
- Overlays render as `absolute` siblings of the viewer canvas inside a `relative` container — preserves `StlViewer.tsx:31`'s `ResizeObserver`.

**Changes (Param rail):**

- Replace `<ParamRail>` placeholder with grouped rail per `screenshots/02-detail-desktop.png`:
  - Group by `param.group`. Ungrouped bucket last.
  - Group header: `font-mono text-10 uppercase tracking-wide text-text-dim`, chevron, collapsible (local `open` state per group, defaults open).
  - `<ParamRow>` per D3 in `components/ParamRow.tsx`.
- **"Download STL" button** moves to the stat strip's right end or a top-right action slot — whichever matches the screenshot at review. Label text preserved verbatim.
- Delete `components/ParamForm.tsx` at end of bead.

**Acceptance:** `tests/e2e/model-page.spec.ts`, `preview-controls.spec.ts`, `live-preview.spec.ts`, `validation.spec.ts` all green unchanged. One new unit test: `<ParamRow>` accepts out-of-range typed value without clamping. One new E2E or unit test: clicking a view-preset tab reorients the camera. Visual parity with `screenshots/02-detail-desktop.png`. Zero inline styles. `ParamForm.tsx` deleted.

## Risks

| Risk | Mitigation |
|---|---|
| `canvas.__stlViewer` debug handle dropped when wrapping viewer | 1.c acceptance explicitly preserves it; extend with `setCameraPreset`, don't replace. Phase-2 follow-up bead moves to a typed `useImperativeHandle` contract. |
| `useRenderer` debounce/cancel semantics drift from existing `ModelStudio` | 1.b ports verbatim in one commit before cosmetic changes. Smoke test for stale-token discard. |
| ResizeObserver breaks when chrome overlays share the viewer container | Use `relative` parent + `absolute` overlays (no layout participation). |

## E2E invariants

Phase 1 does not touch these strings or attributes:

- `id="param-<name>"` on every numeric input (`model-page.spec.ts:13`)
- Literal "Download STL" button label (`model-page.spec.ts:22`)
- `canvas.__stlViewer` debug handle exposing `{ camera, controls }`, extended with `setCameraPreset` (`preview-controls.spec.ts:21`)
- URL format `/models/<slug>` with `_` → `-` (`gallery.spec.ts:7–12`)

## Future phases

- **Phase 2** — compile-error line parsing (fills `renderError.line`), bbox in `RenderResult` (`dimensions` added then), loading progress UI. `useRenderer` contract accommodates without signature change.
- **Phase 3** — presets (`localStorage`, `⌘1`–`⌘9`), command palette, global keyboard shortcut map (moves viewer keys from 1.c into a registry), modified-dot indicator. `DetailState` gains `preset: PresetBinding` as a discriminated union at that time.
- **Phase 4** — print prep, mobile bottom sheet, a11y sweep.
