// Single-model page for the Phase 1 slice. Server-fetches the SCAD
// source for cylinder_holder_46mm_slot.scad, parses its inline @param
// annotations, and hands both off to the client-side <ModelStudio>
// (form + WASM preview).

import fs from "node:fs/promises";
import path from "node:path";
import Link from "next/link";
import ModelStudio from "@/components/ModelStudio";
import { parseScadParams } from "@/lib/scad-params/parse";

const MODEL_REL = "models/cylinder_holder_46mm_slot.scad";

export default async function CylinderHolderPage() {
  const abs = path.resolve(process.cwd(), MODEL_REL);
  const source = await fs.readFile(abs, "utf8");
  const { params, warnings } = parseScadParams(source);

  return (
    <main style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
      <p style={{ marginBottom: "0.5rem" }}>
        <Link href="/" style={{ color: "#7ee787" }}>← all models</Link>
      </p>
      <h1 style={{ marginTop: 0 }}>Multiconnect cylinder holder, 46mm</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Source: <code>{MODEL_REL}</code> · {params.length} parameter
        {params.length === 1 ? "" : "s"}
        {warnings.length > 0 && ` · ${warnings.length} parser warning${warnings.length === 1 ? "" : "s"}`}
      </p>
      {warnings.length > 0 && (
        <pre style={{ background: "#3a1f1f", color: "#ffb4b4", padding: "0.75rem", borderRadius: 4, fontSize: "0.85rem" }}>
          {warnings.join("\n")}
        </pre>
      )}
      <ModelStudio modelPath={MODEL_REL} source={source} params={params} />
    </main>
  );
}
