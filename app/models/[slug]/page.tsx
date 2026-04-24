// Dynamic single-model page. Server component — loads the model from
// disk and hydrates any `?<short>=<value>` share params via the
// decoder, then hands everything to DetailPage (client).

import { notFound } from "next/navigation";
import DetailPage from "@/components/DetailPage";
import { listModels, loadModel } from "@/lib/models/discover";
import { decodeShare, type ShareWarning } from "@/lib/share/encode";
import type { Param, ParamValue } from "@/lib/scad-params/parse";

interface Props {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

export async function generateStaticParams() {
  const models = await listModels();
  return models.map((m) => ({ slug: m.slug }));
}

export default async function ModelPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const rawSearch = await searchParams;
  const model = await loadModel(slug);
  if (!model) notFound();

  const { values: initialValues, warnings: shareWarnings } =
    normalizeAndDecode(model.params, rawSearch);

  return (
    <DetailPage
      model={{
        title: model.title,
        slug: model.slug,
        modelPath: model.modelPath,
        source: model.source,
        params: model.params,
        presets: model.presets,
        warnings: [
          ...model.warnings,
          ...shareWarnings.map(formatShareWarning),
        ],
      }}
      initialValues={initialValues}
    />
  );
}

function normalizeAndDecode(
  params: readonly Param[],
  rawSearch: Record<string, string | string[] | undefined>,
): {
  values: Partial<Record<string, ParamValue>>;
  warnings: ShareWarning[];
} {
  const q = new URLSearchParams();
  for (const [key, value] of Object.entries(rawSearch)) {
    if (value === undefined) continue;
    if (Array.isArray(value)) {
      // Repeated keys (?d=1&d=2) — take the last one, same as
      // navigator does for history state. Warn-don't-fail.
      const last = value[value.length - 1];
      if (last !== undefined) q.set(key, last);
    } else {
      q.set(key, value);
    }
  }
  return decodeShare(params, q);
}

function formatShareWarning(w: ShareWarning): string {
  if (w.kind === "unknown") {
    return `Unknown share-URL parameter "${w.key}" — ignored`;
  }
  return `Share-URL value for "${w.name}" (${JSON.stringify(w.raw)}) invalid: ${w.reason}`;
}
