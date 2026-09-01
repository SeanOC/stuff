// Dynamic single-model page. Server component — loads the model from
// disk, hands a DetailPage the raw fields it needs. All chrome lives
// in DetailPage (client).
//
// Two engines share this route:
//   • scad       → loadModel() + the full live-WASM DetailPage.
//   • build123d  → loadBdModel() + BdDetailPage (P1 preset flow: baked
//                  GLB viewer + preset picker + STL download, no live
//                  params). Gated on BD_MODELS_ENABLED (bead pst-0um9).

import { notFound } from "next/navigation";
import DetailPage from "@/components/DetailPage";
import BdDetailPage from "@/components/BdDetailPage";
import { getAccessoriesForModel } from "@/lib/accessories/discover";
import { listModels, loadModel } from "@/lib/models/discover";
import { bdModelsEnabled, loadBdModel } from "@/lib/models/bd-manifest";

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

  // build123d models have no .scad source, so loadModel returns null.
  // Fall through to the manifest-backed bd detail view when the feature
  // is enabled.
  if (!model) {
    if (bdModelsEnabled()) {
      const bd = await loadBdModel(slug);
      if (bd) {
        return (
          <BdDetailPage
            model={{
              slug: bd.slug,
              title: bd.title,
              blurb: bd.blurb,
              params: bd.params,
              presets: bd.presets,
            }}
          />
        );
      }
    }
    notFound();
  }

  const accessories = await getAccessoriesForModel(model.stem);

  return (
    <DetailPage
      model={{
        title: model.title,
        slug: model.slug,
        modelPath: model.modelPath,
        source: model.source,
        params: model.params,
        presets: model.presets,
        warnings: model.warnings,
      }}
      accessories={accessories.map((a) => ({
        slug: a.slug,
        title: a.title,
        blurb: a.blurb,
        downloadUrl: a.downloadUrl,
        fileSize: a.fileSize,
        attribution: a.attribution,
      }))}
    />
  );
}
