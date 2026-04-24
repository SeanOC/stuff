---
title: Caliper Redesign Phase 3 — Presets, Command Palette, Share
type: feat
date: 2026-04-23
epic: st-gtb
phase: 3
revised: 2026-04-24 (post-3c revert; plan kept as authored for archival)
---

# Caliper Redesign Phase 3 — Presets, Command Palette, Share

> **Update 2026-04-24 (st-jfn):** Phase 3c reverted per user decision —
> URL encoding, share dialog, Toast, and the `⌘⇧C` shortcut were removed.
> Phase 3 final scope = 3a (presets + foundation) + 3b (command palette
> + shortcut sheet). The `Share` sections below are retained as-is for
> archival context; they describe work that did not ship.

Phases 0, 1, 2 are shipped. Phase 3 adds presets (stock inline in source, user in localStorage), a hand-rolled ⌘K palette, a global keyboard registry replacing phase-1c's viewer-local handler, and a share dialog with URL-encoded param snapshots.

## Three beads

```
Phase 0 / 1 / 2 (shipped)
        │
        └── 3a Presets + foundation
                (Modal, useShortcut, useLocalStorage, UIContext reducer,
                 forwardRef StlViewer, SCAD @preset grammar, inline save-row)
                      │
              ┌───────┴────────┐
              ▼                ▼
            3b Palette       3c Share
            (CommandPalette   (shortKey parser, encode/decode,
             + ShortcutSheet,  ShareDialog, minimal Toast,
             ⌘K ⌘L ?)          ⌘⇧C ⌘E)
```

3b and 3c are independent once 3a lands.

## Architectural decisions

### D1. Shared `<Modal>` — single file, focus trap inline

`components/Modal.tsx`. Adds `createPortal` to `#modal-root` (new `<div>` in `app/layout.tsx`), backdrop (`fixed inset-0 bg-bg/60`), body (`rounded-6 shadow-modal border border-line bg-panel`), Escape + backdrop close, autofocus first focusable, restore focus on close, Tab/Shift-Tab trap within the subtree. Focus trap is ~25 lines inlined — no separate hook file. `ErrorLogModal` migrates in 3a (gains focus trap as a side effect).

```tsx
interface ModalProps {
  open: boolean;
  onClose: () => void;
  label: string;                // aria-label
  children: ReactNode;
  className?: string;           // consumer owns width: "w-[560px]"
  dismissOnBackdrop?: boolean;  // default true
}
```

Callers pass Tailwind widths directly (`w-[560px]`, `w-[520px]`, `w-[720px]`). No `widthPx` prop.

### D2. `useShortcut` — hand-rolled, typed Binding union

No library. A single window-level `keydown` listener in `hooks/useShortcut.ts`, ~50 lines total. `$mod` resolves to `e.metaKey` on Mac, `e.ctrlKey` elsewhere. Chord parser splits on `+` and matches modifiers + key. Input-field guard: skip bare keys (`g`, `1`) when focus is in `INPUT/SELECT/TEXTAREA`; always fire modifier chords (user wants `⌘S` in a param input to save).

```ts
const BINDINGS = [
  "$mod+k", "$mod+l", "$mod+s", "$mod+e", "$mod+Shift+c",
  "$mod+1", "$mod+2", "$mod+3", "$mod+4", "$mod+5",
  "$mod+6", "$mod+7", "$mod+8", "$mod+9",
  "1", "2", "3", "g", "d", "f", "r", "Enter", "Escape", "?",
] as const;
type Binding = typeof BINDINGS[number];

function useShortcut(
  binding: Binding,
  handler: (e: KeyboardEvent) => void,
  opts?: { enabled?: boolean; preventDefault?: boolean },
): void;
```

Typed union catches typos and feeds `ShortcutSheet` generation later.

Scope coordination: each caller guards via `opts.enabled`. Viewer keys gate on `!anyModalOpen`; palette's `Escape` gates on `modal.kind === "palette"`. No provider per concern.

### D3. `useLocalStorage` + version prefix

`hooks/useLocalStorage.ts`, ~30 lines. SSR-safe: `useState(fallback)` on mount, `useEffect` reads localStorage on client and updates state if present.

Keys used in phase 3, each with a `v1.` schema prefix so future migrations don't need a rename sweep:

- `stuff.v1.presets.<slug>` — user presets
- `stuff.v1.lastParams.<slug>` — last-edited params
- `stuff.v1.recent.models` — last 5 visited slugs

Keys sit directly at call sites (no `lib/storage.ts` accessor map — three consumers isn't enough to justify indirection).

### D4. `UIContext` — single-slot reducer

One `<UIProvider>` at AppShell level. Discriminated union makes "two modals open at once" impossible:

```ts
type Modal =
  | { kind: "none" }
  | { kind: "palette" }
  | { kind: "share" }
  | { kind: "errorLog" }
  | { kind: "shortcutSheet" };  // 3b adds this

type UIAction = { type: "open"; modal: Modal } | { type: "close" };

function useUI(): { modal: Modal; dispatch: (a: UIAction) => void };
```

Consumers: `modal.kind === "palette"` to read, `dispatch({ type: "open", modal: { kind: "palette" } })` to open. Viewer shortcuts guard on `modal.kind === "none"`. No inline save-preset or prompts need the stack (they're inline DOM rows, not modals — see D7).

### D5. Preset data — inline `@preset` SCAD annotations

Extend the `@param` parser to also handle `@preset`:

```scad
// @preset id="42mm-cylinder" label="42mm cylinder" can_diameter=42 clearance=0.25 ring_height=50
```

The existing `key=value` attribute parser at `lib/scad-params/parse.ts:194` handles this verbatim. Add a minimal `parsePresets(source)` that scans for `@preset` lines and returns `Preset[]`. Values coerce to the declared param's kind at parse time (fail parse on type mismatch — catches author typos).

Why inline, not sidecar JSON: presets are model metadata, not ops config. Keeping one file per model preserves the "one file = one model" story the README authoring loop leans on. Parser already has the attribute grammar, so the extension is ~20 lines.

CI gate: `scripts/check-invariants.py` adds one check — every `@preset` key matches a declared `@param`, values are in-kind (fails on drift). Warn-don't-fail on out-of-range (phase 1 explicitly allows typed out-of-range values).

User presets (localStorage) use the same shape + a `savedAt` ISO string.

### D6. Preset binding state — nullable pair, not DU

```ts
type DetailState = {
  params: Record<string, ParamValue>;
  camera: "top" | "front" | "iso";
  showGrid: boolean;
  showDims: boolean;
  activePresetId: string | null;
  modified: boolean;
};
```

Two states don't need a DU. `activePresetId=null, modified=true` is not a real bug (means "user edited without a bound preset") — meaningful state for the modified-dot UI. Upgrade to DU only when a concrete third state appears (e.g. "auto-rebind on match").

`paramsEqual` helper inlined at the bottom of `hooks/useDetailState.ts`, ~10 lines. Plain `===` comparison per-param. No float-tolerance epsilon — add when a test actually fails.

### D7. Save-preset UX — inline row, not modal

Spec wants `⌘S` to save. Default behavior: show an inline row at the top of the preset list with a text input ("Preset name…"), Save button, Escape cancels. No modal. Simpler UX (no hop), simpler code (one component, no extra Modal instance).

### D8. `ParamBase.shortKey` — non-optional post-parse

Parser sets `shortKey = name` if `short=` attribute is absent. Post-parse, every param has a unique `shortKey: string`. No `?? name` fallback at call sites.

Uniqueness: parser validates all `shortKey`s in a file are distinct, throws on collision.

### D9. URL encode/decode with warnings

```ts
// lib/share/encode.ts
export function encodeShare(
  params: readonly Param[],
  values: Record<string, ParamValue>,
): string;

type DecodeResult = {
  values: Partial<Record<string, ParamValue>>;
  warnings: Array<
    | { kind: "unknown"; key: string }
    | { kind: "invalid"; name: string; raw: string; reason: string }
  >;
};
export function decodeShare(
  params: readonly Param[],
  query: URLSearchParams,
): DecodeResult;
```

`encode` emits `<shortKey>=<value>` only for params that differ from defaults (short URLs). Booleans as `1`/`0`, enums as literal strings.

`decode` returns partial + warnings. `useDetailState` merges `values` over defaults; warnings route into the existing error-log panel (phase 2a) so mangled URLs don't degrade silently.

### D10. URL hydration + no `/m/` redirect

`app/models/[slug]/page.tsx` accepts Next 16's `searchParams` promise, resolves + passes `initialValues` to `<DetailPage>`. `useDetailState` initializer prefers `initialValues` > `localStorage[stuff.v1.lastParams.<slug>]` > defaults.

Share URL is `/models/<slug>?<short>=<value>&...`. No `/m/` alias — four extra characters in a pasted URL isn't worth the extra route file (DHH + Simplicity both killed this in review).

### D11. `forwardRef` StlViewer — stop extending the escape hatch

Phase 1 shipped `canvas.__stlViewer = { camera, controls }` as "temporary." Phase 1c added `setCameraPreset`. Phase 3 adds `resetCamera`. Third expansion — cut bait.

```tsx
export interface StlViewerHandle {
  camera: PerspectiveCamera;
  controls: OrbitControls;
  setCameraPreset(preset: "top" | "front" | "iso"): void;
  resetCamera(): void;
}
export const StlViewer = forwardRef<StlViewerHandle, Props>(...);
```

E2E compatibility shim: dev-only `useEffect` still attaches the handle to `canvas.__stlViewer` so existing `preview-controls.spec.ts` assertions work.

```tsx
useEffect(() => {
  if (process.env.NODE_ENV === "production") return;
  const handle = handleRef.current;
  if (canvasRef.current && handle) {
    (canvasRef.current as unknown as { __stlViewer?: StlViewerHandle }).__stlViewer = handle;
  }
}, []);
```

Viewer keys (D12) use the ref, not the global.

### D12. Viewer keys — migrate to `useShortcut`

Delete `ViewerChrome.handleKeyDown`. Replace with `useShortcut` calls:

```tsx
const gate = modal.kind === "none" && focusInViewer;
useShortcut("1", () => choose("top"),   { enabled: gate });
useShortcut("2", () => choose("front"), { enabled: gate });
useShortcut("3", () => choose("iso"),   { enabled: gate });
useShortcut("g", toggleGrid,      { enabled: gate });
useShortcut("d", toggleDims,      { enabled: gate });
useShortcut("f", toggleFullscreen, { enabled: gate });
useShortcut("r", resetCamera,     { enabled: gate });
useShortcut("Enter", onRefresh,   { enabled: gate && state.kind === "idle" });
```

`focusInViewer` tracks whether the active element is within the viewer section (maintain via `onFocus/onBlur` on the `<section>`).

### D13. Command palette — hand-rolled, spec group order

`components/CommandPalette.tsx`, ~200 lines. Modal `w-[560px]`. Inline command array (no `lib/palette/commands.ts` — builder function for 3 models + 5 actions is over-indirection). Groups in spec order: **Models · Actions · Presets · Recent** (spec wins over the design mock's `Models · Presets · Actions · Navigate`, per README:76).

Substring search on label + blurb. ↑↓ cursor, Enter activates, Escape closes.

Shortcut sheet is a separate static Modal (not derived from commands) — no registry coupling. Drift risk on ~15 bindings is small; a TODO comment in `CommandPalette` reminds whoever touches shortcuts to sync the sheet.

Recent models: inline LRU (~6 lines) in `DetailPage` mount effect that updates `stuff.v1.recent.models`. Palette reads via `useLocalStorage`.

### D14. Share dialog — no dead UI, minimal toast

`components/ShareDialog.tsx`. Modal `w-[520px]`. Buttons:
- **Copy link** — copies full `/models/<slug>?...` URL.
- **Download .json** — downloads `<slug>-params.json`.

"Copy short" **not rendered** (deleted from UI until a short-URL service is wired — follow-up bead).

On success: dialog closes + a small `<Toast>` (~30 lines, portals to `#modal-root`, `aria-live="polite"`, 2s auto-dismiss) appears bottom-right. Toast is also used by `⌘⇧C` direct-copy path (no dialog opens — toast confirms).

### D15. Deferrals

- **`⌘P` print prep** — phase 4.
- **`⌘/` source view** — no source-view UI mode in phase 3 (quick-jump in left rail stays). Phase 4 or later.
- **`⌘,` preferences** — no prefs panel in phase 3.
- **Copy short** — follow-up bead when short-URL service is picked.
- **Multi-tab localStorage sync** — single-tab model. No `storage` event listener.
- **Auto-rebind on preset-match** — stays "dumb tracker" per D6.

## Bead 3a — Presets + foundation

**Changes:**

- `components/Modal.tsx` (new) + `#modal-root` in `app/layout.tsx`.
- `hooks/useShortcut.ts` (new, hand-rolled, typed Binding union).
- `hooks/useLocalStorage.ts` (new).
- `contexts/UIContext.tsx` (new, reducer-single-slot).
- `<Toast>` stubbed but not yet used — move to 3c when needed. *Revised:* skip in 3a. Add in 3c alongside its consumer.
- `components/StlViewer.tsx` — `forwardRef` migration + dev-only `__stlViewer` shim.
- `components/ViewerChrome.tsx` — delete `handleKeyDown`, replace with `useShortcut`. Migrate `ErrorLogModal` to shared `<Modal>` (kills ~50 lines of inline modal code; gains focus trap).
- `lib/scad-params/parse.ts` — add `@preset` grammar + `Preset[]` return. Add `shortKey` handling (non-optional post-parse). Validate uniqueness.
- All three `.scad` models — seed `@preset` lines. Add `short=` to every `@param`.
- `hooks/useDetailState.ts` — add `activePresetId`, `modified`. Add `loadPreset(id)`, mutator that replaces all params in one transition. Recompute `modified` on `setParam` via inline `paramsEqual`.
- `components/DetailLeftRail.tsx` — replace phase-1 stub with real preset list (clickable rows, modified-dot, inline save-row at top).
- Shortcuts: `⌘1`–`⌘9` load presets by index (stock first, user after; truncated to 9); `⌘S` activates the inline save-row; `⌘E` downloads STL (wires to existing DownloadButton).
- `scripts/check-invariants.py` — add `@preset` validity check.

**Acceptance:**

- ErrorLogModal still works (Escape, backdrop). Tab stays trapped inside.
- Viewer keys (1/2/3/G/D/F/R/Enter) work via `useShortcut`.
- Preset list in left rail for all three models; click loads; modified-dot on any edit.
- `⌘S` opens inline save-row; typing a name + Enter saves to localStorage.
- `⌘1`–`⌘9` load by index.
- `preview-controls.spec.ts` (`__stlViewer` handle) still passes — dev shim keeps the E2E path.
- `scripts/check-invariants.py` fails on a preset with an unknown param key.
- `npm run build` green. All E2E + vitest green.

## Bead 3b — Command palette + shortcut sheet

Depends on 3a.

**Changes:**

- `components/CommandPalette.tsx` (new, inline command array, grouped).
- `components/ShortcutSheet.tsx` (new, static content mirroring `share-and-shortcuts.jsx`'s ShortcutSheet).
- `components/AppShell.tsx` — wire top-bar `⌘K` button to `dispatch({ type: "open", modal: { kind: "palette" } })`. Remove `disabled`.
- Recent-models LRU (inline in `DetailPage` mount effect).
- Shortcuts: `⌘K` opens palette, `⌘L` navigates to `/`, `?` opens ShortcutSheet.

**Acceptance:**

- `⌘K` opens palette from anywhere.
- Substring filter works across Models/Actions/Presets/Recent.
- ↑↓ Enter Escape all behave.
- Selecting a model navigates; selecting an action fires the action.
- `⌘L` navigates to library; `?` opens shortcut sheet.
- New E2E spec `tests/e2e/command-palette.spec.ts` covers open/search/navigate/activate.

## Bead 3c — Share dialog + URL encoding

Depends on 3a.

**Changes:**

- `lib/share/encode.ts` (new, `encodeShare` + `decodeShare` with warnings).
- `app/models/[slug]/page.tsx` — accept `searchParams`, pass `initialValues` to DetailPage.
- `hooks/useDetailState.ts` — initializer consumes `initialValues` (URL > localStorage > defaults priority).
- `components/ShareDialog.tsx` (new, Copy link + Download .json only).
- `components/Toast.tsx` (new, ~30 lines).
- `components/DetailHeader.tsx` — add Share button.
- Shortcuts: `⌘⇧C` direct-copy + toast (no dialog).

**Acceptance:**

- `/models/cylindrical-holder-slot?d=70&c=0.25` hydrates params from query.
- Share dialog Copy link copies URL, fires toast, closes.
- `⌘⇧C` from detail copies + toasts without opening dialog.
- Download .json produces valid JSON with model slug + params.
- Warnings from `decodeShare` route to error-log panel for display.
- New E2E spec `tests/e2e/share-dialog.spec.ts` covers copy, download, URL round-trip.

## Risks

| Risk | Mitigation |
|---|---|
| Hand-rolled shortcut guards miss a cross-platform edge case | Test `⌘S`/`⌘⇧C` on Firefox, Safari, Chrome. Add E2E that asserts chord fires. |
| Focus trap breaks an unusual modal (select text in dimmed backdrop) | Backdrop is inert. Trap scope is the modal body. |
| `@preset` grammar collides with a future `@param` attribute | Parser requires `@preset` at line start, not as a `@param` attribute. Separate parse path. |
| `__stlViewer` shim leaks into production bundle | `process.env.NODE_ENV === "production"` early-return; verify via `grep __stlViewer .next/` post-build. |
| URL hydration + localStorage conflict | Priority: URL > localStorage > defaults. Documented in `useDetailState` comment. |

## E2E invariants preserved

- `#param-<name>` on every numeric input.
- `canvas.__stlViewer` debug handle (via dev shim) still readable from Playwright.
- "Download STL" button label.
- `/models/<slug>` URLs (now optionally with `?...`).
- Viewer keys 1/2/3/G/D/F/Enter.

## Future phases

- **Phase 4**: print prep (`⌘P`), mobile bottom sheet (< 720 px), `⌘,` prefs, `⌘/` source view, short-URL service wiring (Copy short), a11y sweep.
- **Nice-to-have bucket**: fuzzy palette match, multi-tab localStorage sync, preset import/export.

## References

- `docs/design/caliper/README.md` § "Presets", "Command palette", "Share", "Keyboard Shortcuts"
- `docs/design/caliper/design_files/caliper.jsx:790–871` (cmdk mock)
- `docs/design/caliper/design_files/share-and-shortcuts.jsx` (share + ShortcutSheet authoritative)
- `docs/design/caliper/screenshots/04-command-palette.png`, `09-share-dialog.png`, `10-shortcuts-reference.png`
- `docs/plans/2026-04-22-feat-caliper-redesign-phase-1-plan.md` (patterns phase 3 extends)
- `components/ViewerChrome.tsx:475–527` (ErrorLogModal — migrates in 3a)
