// Test-only route that renders DetailPage against a deliberately
// malformed .scad fixture (tests/fixtures/models/broken_syntax.scad)
// so the E2E suite can exercise the error-strip + log-modal UI
// without needing a real model to parse-fail (st-yom).
//
// Gate: enabled when NODE_ENV !== "production" (e.g. `next dev`) OR
// when STUFF_ENABLE_TEST_ROUTES=1 is set on the process. The E2E
// config passes the env var to `next start` / `next dev` in both
// local and CI runs; production builds on Vercel don't set it, so
// this route 404s there. The main /models/[slug] route stays
// statically generated — this one is dynamic on purpose
// (force-dynamic, so the fixture-read always hits disk and picks
// up fixture edits in dev).
//
// Path chosen as app/dev/ rather than app/__test/ because Next.js
// treats leading-underscore folders as private (non-routable).

import fs from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import DetailPage from "@/components/DetailPage";

export const dynamic = "force-dynamic";

function testRoutesEnabled(): boolean {
  return (
    process.env.NODE_ENV !== "production" ||
    process.env.STUFF_ENABLE_TEST_ROUTES === "1"
  );
}

export default async function BrokenSyntaxPage() {
  if (!testRoutesEnabled()) notFound();

  const abs = path.resolve(
    process.cwd(),
    "tests/fixtures/models/broken_syntax.scad",
  );
  let source: string;
  try {
    source = await fs.readFile(abs, "utf8");
  } catch {
    notFound();
  }

  return (
    <DetailPage
      model={{
        title: "broken syntax fixture (test-only)",
        modelPath: "tests/fixtures/models/broken_syntax.scad",
        source,
        params: [],
        warnings: [],
      }}
    />
  );
}
