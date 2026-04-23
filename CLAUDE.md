# Project Instructions for AI Agents

This file provides context for AI coding agents working on this project.

## Issue tracking — beads (`bd`)

This project uses [beads](https://github.com/steveklabnik/beads) for issue
tracking. Run `bd prime` to see the full command reference.

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

Use `bd` for task tracking; don't maintain parallel markdown TODO lists.

## Build, test, lint

```bash
npm install           # Install web-app deps
npm run dev           # Local dev server on http://localhost:3000
npm test              # Vitest unit tests
npm run test:e2e      # Playwright end-to-end tests
npm run build         # Production Next.js build
```

Model-level checks (OpenSCAD renders + per-model invariants) — see
[AGENTS.md](AGENTS.md) for the render pipeline and invariants sidecar
convention.

## Architecture overview

- `app/` — Next.js App Router frontend. Gallery at `/`, dynamic detail
  page at `/models/[slug]`. Server components load `.scad` sources
  from disk; the client re-renders on param edits via
  `openscad-wasm-prebuilt`.
- `components/` — React UI (StlViewer, DetailPage, ParamRail, etc.).
- `hooks/` — `useRenderer`, `useDetailState`.
- `lib/scad-params/` — pure TS parser for `@param` annotations in
  `.scad` files (source of truth for auto-generated form controls).
- `lib/wasm/` — browser-side WASM render driver + include-closure walker.
- `lib/models/` — filesystem-backed model discovery.
- `models/` — parametric `.scad` sources. Each model ships a sidecar
  `<stem>.invariants.py` asserting machine-checkable claims.
- `libs/` — vendored OpenSCAD libraries (BOSL2, QuackWorks). Pinned
  in `libs/README.md`; cloned by `scripts/vendor-libs.sh`.
- `scripts/` — Python tooling: render-all, export-all, invariants,
  artifact server.
- `.claude/skills/` — project-local Claude Code skills (`scad-new`,
  `scad-render`, `scad-export`, `scad-lib`, `scad-send`).

## Remote artifact browser

`scripts/serve.py` is a read-only HTTP server (stdlib only) that lists
every `models/*.scad`, its render thumbnails under `renders/<stem>/`,
and its `exports/<stem>.stl` download. Useful when the dev host is
headless but you want to eyeball renders from a laptop. Binds
`0.0.0.0:8765` by default — assumes a trusted network since there's no
auth. Pass `--host 127.0.0.1` to restrict to loopback.

```bash
python3 scripts/serve.py                       # http://<host>:8765/
python3 scripts/serve.py --host 127.0.0.1      # loopback only
ssh -NL 8765:127.0.0.1:8765 dev-host           # forward to laptop
```
