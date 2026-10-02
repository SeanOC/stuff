// Live STL download filenames. A param flagged `filename` (SCAD: bare word on
// its @param line; build123d: Param(filename=True) → manifest) names the
// download after its current value, so the three spool-cradle mount styles
// download as holder-spool-cradle-{channel,points,openconnect}.stl.
//
// Mirrors scripts/export-all.py plan_variants so a live download and the baked
// export of the same variant share a name: one flagged param → `<stem>-<value>`,
// several → `<stem>-<k1>=<v1>-<k2>=<v2>`. Flagged params are ALWAYS included
// (defaults too) so the name is stable; unflagged models keep `<stem>.stl`.
// Number/integer flags are live-only (export-all fans out enums only) and read
// `-<name><value>` for a single flag so a bare number is never ambiguous.
//
// The stem is used verbatim — SCAD stems keep their underscores, build123d
// slugs are already dash-form — only VALUES are sanitised.

import type { Param, ParamValue } from "../scad-params/parse";

// Lowercase, then collapse anything outside [a-z0-9_.-] (spaces, quotes,
// slashes, non-ASCII) to "-". Underscores stay: baked SCAD names keep them
// (e.g. cap_left, multiconnect_plate). Keeps the value safe inside a quoted
// Content-Disposition filename.
function sanitize(value: ParamValue): string {
  return (
    String(value)
      .toLowerCase()
      .replace(/[^a-z0-9_.-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "none"
  );
}

export function downloadFilename(
  stem: string,
  params: Param[],
  values: Record<string, ParamValue>,
  ext = "stl",
): string {
  const flagged = params.filter((p) => p.filename);
  if (flagged.length === 0) return `${stem}.${ext}`;
  const valueOf = (p: Param) => sanitize(values[p.name] ?? p.default);
  let suffix: string;
  if (flagged.length === 1) {
    const [p] = flagged;
    const numeric = p.kind === "number" || p.kind === "integer";
    suffix = numeric ? `${p.name}${valueOf(p)}` : valueOf(p);
  } else {
    suffix = flagged.map((p) => `${p.name}=${valueOf(p)}`).join("-");
  }
  return `${stem}-${suffix}.${ext}`;
}
