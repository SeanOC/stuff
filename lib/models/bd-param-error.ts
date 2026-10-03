// Which param a live render's 400 is about, so BdDetailPage can show the
// message under that row (labels L4, pst-egc3j).
//
// Validation messages lead with the param name — the route's pre-check
// (`param d: …`) and the service's registry checks (`text: 25 characters
// > max length 24`). A build-time rejection names none (label text below
// the stroke floor): on a model with exactly one free-text param it can
// only be about that text; otherwise it stays in the viewer banner only.

import type { Param } from "@/lib/scad-params/parse";

export function paramErrorsFor(params: Param[], message: string): Record<string, string> {
  const named = params.find(
    (p) => message.startsWith(`${p.name}:`) || message.startsWith(`param ${p.name}:`),
  );
  if (named) return { [named.name]: message };
  const strings = params.filter((p) => p.kind === "string");
  return strings.length === 1 ? { [strings[0].name]: message } : {};
}
