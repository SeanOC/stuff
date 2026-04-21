// Dynamic single-model page. Replaces the Phase 1 hardcoded
// /models/cylinder-holder-46 route.

import Link from "next/link";
import { notFound } from "next/navigation";
import ModelStudio from "@/components/ModelStudio";
import { listModels, loadModel } from "@/lib/models/discover";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const models = await listModels();
  return models.map((m) => ({ slug: m.slug }));
}

export default async function ModelPage({ params }: Props) {
  const { slug } = await params;
  const model = await loadModel(slug);
  if (!model) notFound();

  return (
    <main style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
      <p style={{ marginBottom: "0.5rem" }}>
        <Link href="/" style={{ color: "#7ee787" }}>← all models</Link>
      </p>
      <h1 style={{ marginTop: 0 }}>{model.title}</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        Source: <code>{model.modelPath}</code> · {model.params.length} parameter
        {model.params.length === 1 ? "" : "s"}
        {model.warnings.length > 0 && ` · ${model.warnings.length} parser warning${model.warnings.length === 1 ? "" : "s"}`}
      </p>
      {model.warnings.length > 0 && (
        <pre style={{ background: "#3a1f1f", color: "#ffb4b4", padding: "0.75rem", borderRadius: 4, fontSize: "0.85rem" }}>
          {model.warnings.join("\n")}
        </pre>
      )}
      <ModelStudio modelPath={model.modelPath} source={model.source} params={model.params} />
      {model.params.length === 0 && (
        <p style={{ marginTop: "1rem", color: "#8b949e", fontSize: "0.85rem" }}>
          <em>Parameters not yet annotated</em> — this model renders with its
          file defaults. Add inline <code>// @param</code> annotations under a{" "}
          <code>// === User-tunable parameters ===</code> header to expose
          sliders.
        </p>
      )}
    </main>
  );
}
