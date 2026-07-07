// Native render service — Phase 1 spike (st-065, plan in st-rtb).
//
// A tiny stdlib-only HTTP server that wraps a native, headless
// `openscad -o out.stl -D <defines> <model>` behind POST /render. It
// exists to replace the ~22s openscad-wasm render on /api/export's
// cache-miss path (Phase 2) with a native ~seconds render, without
// changing outputs.
//
// PARITY: param -> `-D` define coercion REUSES lib/scad-params/parse.ts
// (formatScadLiteral, the exact function the WASM path's
// applyParamOverrides uses), so the same params produce the same
// geometry — and therefore the same st-uqk content-addressed cache key.
//
// SECURITY (spike-level, mirrors app/api/export/route.ts):
//   1. Path regex: ^(models|tests/fixtures)/[A-Za-z0-9._/-]+\.scad$
//   2. Path-resolve confinement under the baked models/ (+ fixtures) root
//   3. Body shape (model:string, params:object), bounded body size
//   4. Every param key must exist in the parsed @param manifest
//   5. Every param value must match its declared kind (and enum choices)
// 1-2 => 403; malformed/oversize/param errors => 400; render failure => 500.
//
// RESPONSE CONTRACT (mirrors lib/wasm/render.ts RenderResult):
//   - success: 200, content-type application/sla, body = raw STL bytes,
//     with the non-byte RenderResult fields in x-* headers
//     (x-render-ms, x-attempts, x-render-ok). Raw bytes rather than a
//     base64 field keeps a 6 MB STL from bloating into 8 MB of JSON and
//     matches how /api/export already returns an STL — Phase 2 reads the
//     body + headers straight into a RenderResult.
//   - failure: 4xx/5xx, content-type application/json,
//     { ok:false, errorMessage, stderr?, attempts? }.

import http from "node:http";
import path from "node:path";
import {
  defaultsOf,
  formatScadLiteral,
  parseScadParams,
  type Param,
  type ParamValue,
} from "../../lib/scad-params/parse";
import fs from "node:fs/promises";
import { renderToStl } from "./render";

const REPO_ROOT = process.env.RENDER_REPO_ROOT ?? process.cwd();
const MODELS_ROOT = path.resolve(REPO_ROOT, "models");
const FIXTURES_ROOT = path.resolve(REPO_ROOT, "tests/fixtures");
const LIBS_ROOT = process.env.OPENSCADPATH ?? path.resolve(REPO_ROOT, "libs");
const MODEL_PATH_RE = /^(?:models|tests\/fixtures)\/[A-Za-z0-9._/-]+\.scad$/;
// Wrap openscad in xvfb-run unless RENDER_XVFB=0. The proven CI export
// path (.claude/skills/_lib/export.py) always uses xvfb-run; some
// openscad builds want a display even for headless STL export.
const USE_XVFB = process.env.RENDER_XVFB !== "0";
// Bound the request body: a params object is tiny; anything large is a
// mistake or abuse. 64 KiB is generous.
const MAX_BODY_BYTES = 64 * 1024;
const PORT = Number(process.env.PORT ?? 8080);

interface ExportBody {
  model: string;
  params?: Record<string, unknown>;
}

const server = http.createServer((req, res) => {
  handle(req, res).catch((e) => {
    // Last-resort guard: never leak a stack, never hang the socket.
    console.error("unhandled:", e);
    if (!res.headersSent) sendJson(res, 500, { ok: false, errorMessage: "internal error" });
    else res.end();
  });
});

async function handle(req: http.IncomingMessage, res: http.ServerResponse) {
  if (req.method === "GET" && (req.url === "/health" || req.url === "/healthz")) {
    return sendJson(res, 200, { ok: true });
  }
  if (req.method !== "POST" || req.url !== "/render") {
    return sendJson(res, 404, { ok: false, errorMessage: "not found" });
  }

  let raw: string;
  try {
    raw = await readBody(req);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return sendJson(res, 413, { ok: false, errorMessage: msg });
  }

  let body: ExportBody;
  try {
    body = JSON.parse(raw) as ExportBody;
  } catch {
    return sendJson(res, 400, { ok: false, errorMessage: "invalid JSON body" });
  }
  if (typeof body?.model !== "string") {
    return sendJson(res, 400, { ok: false, errorMessage: "body.model must be a string" });
  }
  if (
    body.params !== undefined &&
    (typeof body.params !== "object" || body.params === null || Array.isArray(body.params))
  ) {
    return sendJson(res, 400, { ok: false, errorMessage: "body.params must be an object" });
  }

  if (!MODEL_PATH_RE.test(body.model)) {
    return sendJson(res, 403, { ok: false, errorMessage: "model path not allowed" });
  }
  const abs = path.resolve(REPO_ROOT, body.model);
  if (!abs.startsWith(MODELS_ROOT + path.sep) && !abs.startsWith(FIXTURES_ROOT + path.sep)) {
    return sendJson(res, 403, { ok: false, errorMessage: "model path escapes allowed roots" });
  }

  let source: string;
  try {
    source = await fs.readFile(abs, "utf8");
  } catch (e) {
    if ((e as NodeJS.ErrnoException).code === "ENOENT") {
      return sendJson(res, 404, { ok: false, errorMessage: "model not found" });
    }
    throw e;
  }

  const { params: manifest } = parseScadParams(source);
  const validated = validateAndCoerce(manifest, body.params ?? {});
  if ("error" in validated) {
    return sendJson(res, 400, { ok: false, errorMessage: validated.error });
  }

  // Emit a `-D` define for EVERY declared param with defaults resolved —
  // the same set applyParamOverrides rewrites in the WASM path — so the
  // native render is byte-equivalent regardless of which params the
  // caller sent explicitly.
  const defines = manifest.map(
    (p) => `${p.name}=${formatScadLiteral(p, validated.values[p.name] ?? p.default)}`,
  );

  const result = await renderToStl({
    modelPath: abs,
    defines,
    openscadPath: LIBS_ROOT,
    xvfb: USE_XVFB,
  });

  if (!result.ok || !result.stl) {
    return sendJson(res, 500, {
      ok: false,
      errorMessage: result.errorMessage ?? "render failed",
      stderr: result.stderr.slice(-12),
      attempts: result.attempts,
    });
  }

  const filename = path.basename(body.model, ".scad") + ".stl";
  res.writeHead(200, {
    "content-type": "application/sla",
    "content-length": String(result.stl.byteLength),
    "content-disposition": `attachment; filename="${filename}"`,
    "x-render-ok": "true",
    "x-render-ms": result.wallMs.toFixed(0),
    "x-attempts": String(result.attempts),
  });
  res.end(Buffer.from(result.stl));
}

interface ValidatedParams {
  values: Record<string, ParamValue>;
}
interface ValidationError {
  error: string;
}

// Mirror of app/api/export/route.ts validateAndCoerce/coerce so the two
// endpoints reject and coerce params identically.
function validateAndCoerce(
  manifest: Param[],
  raw: Record<string, unknown>,
): ValidatedParams | ValidationError {
  const byName = new Map(manifest.map((p) => [p.name, p]));
  for (const key of Object.keys(raw)) {
    if (!byName.has(key)) return { error: `unknown param: ${key}` };
  }
  const out = defaultsOf(manifest);
  for (const [key, rawVal] of Object.entries(raw)) {
    const param = byName.get(key)!;
    const coerced = coerce(param, rawVal);
    if (coerced === null) return { error: `param ${key}: invalid ${param.kind} value` };
    out[key] = coerced;
  }
  return { values: out };
}

function coerce(param: Param, raw: unknown): ParamValue | null {
  switch (param.kind) {
    case "number":
    case "integer": {
      const n = typeof raw === "number" ? raw : Number(raw);
      if (!Number.isFinite(n)) return null;
      return param.kind === "integer" ? Math.trunc(n) : n;
    }
    case "boolean":
      if (typeof raw === "boolean") return raw;
      if (raw === "true") return true;
      if (raw === "false") return false;
      return null;
    case "enum": {
      const s = String(raw);
      return param.choices.includes(s) ? s : null;
    }
    case "string":
      return typeof raw === "string" ? raw : String(raw);
  }
}

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (c: Buffer) => {
      size += c.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error(`request body exceeds ${MAX_BODY_BYTES} bytes`));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function sendJson(res: http.ServerResponse, status: number, payload: unknown) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "content-type": "application/json",
    "content-length": String(Buffer.byteLength(body)),
  });
  res.end(body);
}

server.listen(PORT, () => {
  console.log(`render service listening on :${PORT} (models=${MODELS_ROOT}, libs=${LIBS_ROOT}, xvfb=${USE_XVFB})`);
});
