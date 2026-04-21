# wasm-spike (st-556 Phase 0)

Throwaway research harness. Determines whether `openscad-wasm` can
render the repo's library stack (BOSL2 + QuackWorks). One-shot.

- `harness.mjs` — runs the bead's three probes back-to-back, prints a
  JSON report.
- `probe1_cube.mjs`, `probe_help.mjs` — scratch scripts kept for
  diagnostics; safe to delete once the spike is closed.
- `findings.md` — verdict, build details, per-probe numbers,
  recommendations for Phase 1.
- `package.json` — only dep is `openscad-wasm-prebuilt`.

```bash
npm install
node harness.mjs
```

This whole directory is intended to be removable once Phase 1 lands.
