// Pull a user-meaningful {line, message} out of OpenSCAD's stderr.
//
// OpenSCAD prints parser/evaluator complaints in a small family of
// shapes, all starting with `ERROR:`. Match the first `ERROR:` block
// (ignoring WARNINGs that often precede it), extract the first numeric
// line reference (`line 42`) if any, and return the rest of the line
// as the message. Errors without a line (`Unterminated multi-line
// comment`) return `line: null` — callers render that cleanly.
//
// Pure — no React, no DOM. Covered by render-error.test.ts.

export interface ParsedRenderError {
  /** First numeric `line N` reference in the first ERROR: block, or null. */
  line: number | null;
  /** The first ERROR: line, minus the `ERROR:` prefix and surrounding whitespace. */
  message: string;
}

const ERROR_PREFIX_RE = /^\s*ERROR:\s*/i;
// Match `line N`, `line: N`, `in file "X", line N`, etc. Case-insensitive,
// word-boundary on the number so `line10foo` doesn't false-positive.
const LINE_REF_RE = /\bline[:\s]*(\d+)\b/i;

/**
 * Parse a multi-line stderr blob; return the first useful error or null
 * when no line in the input starts with `ERROR:`.
 */
export function parseRenderError(stderr: string): ParsedRenderError | null {
  if (!stderr) return null;
  for (const raw of stderr.split(/\r?\n/)) {
    const line = raw.trimEnd();
    if (!ERROR_PREFIX_RE.test(line)) continue;
    const message = line.replace(ERROR_PREFIX_RE, "").trim();
    const m = line.match(LINE_REF_RE);
    const lineNo = m ? Number(m[1]) : null;
    return {
      line: Number.isFinite(lineNo) ? lineNo : null,
      message: message || "render failed",
    };
  }
  return null;
}
