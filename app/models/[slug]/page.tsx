// Dynamic single-model page. Server component — loads the model from
// disk, hands a DetailPage the raw fields it needs. All chrome lives
// in DetailPage (client).

import { notFound } from "next/navigation";
import DetailPage from "@/components/DetailPage";
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
    <DetailPage
      model={{
        title: model.title,
        modelPath: model.modelPath,
        source: model.source,
        params: model.params,
        warnings: model.warnings,
      }}
    />
  );
}
