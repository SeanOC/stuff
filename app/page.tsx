import Link from "next/link";
import clsx from "clsx";
import { listModels, type ModelEntry } from "@/lib/models/discover";
import { MODEL_CATEGORIES } from "@/lib/models/catalog";

export default async function Home() {
  const models = await listModels();
  const byCategory = groupByCategory(models);
  const totalParams = models.reduce((n, m) => n + m.paramCount, 0);

  return (
    <div className="flex min-h-[calc(100vh-38px)]">
      <aside
        className="hidden shrink-0 border-r border-line bg-panel min-[1200px]:block w-220"
        aria-label="Categories"
      >
        <nav className="flex flex-col py-10">
          <div className="px-12 pb-6 font-mono text-10 uppercase tracking-wide text-text-mute">
            Library
          </div>
          {MODEL_CATEGORIES.map((cat) => {
            const count = byCategory.get(cat.id)?.length ?? 0;
            return (
              <a
                key={cat.id}
                href={`#shelf-${cat.id}`}
                className={clsx(
                  "flex items-center justify-between px-12 py-6 text-12 text-text-dim",
                  "hover:bg-panel-hi hover:text-text",
                )}
              >
                <span>{cat.label}</span>
                <span className="font-mono text-10 text-text-mute">{count}</span>
              </a>
            );
          })}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 px-24 py-24">
        <div className="mb-18 flex items-baseline justify-between gap-14">
          <div>
            <h1 className="m-0 text-22 font-semibold">
              Parametric things.
              <span className="text-text-dim font-normal"> Tweak. Render. Print.</span>
            </h1>
            <p className="mt-6 font-mono text-10 uppercase tracking-wide text-text-mute">
              Library · {models.length} {models.length === 1 ? "model" : "models"} ·{" "}
              {totalParams} params
            </p>
          </div>
        </div>

        {MODEL_CATEGORIES.map((cat) => {
          const entries = byCategory.get(cat.id) ?? [];
          if (entries.length === 0) return null;
          return (
            <section
              key={cat.id}
              id={`shelf-${cat.id}`}
              className="mb-28"
              aria-labelledby={`shelf-${cat.id}-heading`}
            >
              <div className="mb-10 flex items-baseline justify-between border-b border-line pb-6">
                <h3
                  id={`shelf-${cat.id}-heading`}
                  className="m-0 font-mono text-11 uppercase tracking-wide text-text-dim"
                >
                  {cat.label}
                </h3>
                <span className="font-mono text-10 text-text-mute">
                  {entries.length}
                </span>
              </div>
              <div className="grid grid-cols-1 min-[768px]:grid-cols-2 min-[1200px]:grid-cols-3 gap-14">
                {entries.map((m) => (
                  <ModelCard key={m.slug} m={m} />
                ))}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}

function ModelCard({ m }: { m: ModelEntry }) {
  return (
    <Link
      href={`/models/${m.slug}`}
      className={clsx(
        "flex flex-col overflow-hidden rounded-4 border border-line bg-panel",
        "no-underline text-text transition-colors",
        "hover:border-accent-line hover:bg-panel-hi",
      )}
    >
      <div className="aspect-[4/3] overflow-hidden border-b border-line-soft bg-panel2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/thumbnail?model=${encodeURIComponent(m.slug)}`}
          alt={`top view of ${m.title}`}
          className="h-full w-full object-cover"
        />
      </div>
      <div className="flex flex-col gap-4 p-12">
        <div className="text-13 font-semibold text-text">{m.title}</div>
        <code className="font-mono text-10 text-text-mute">{m.stem}.scad</code>
        <p className="m-0 text-12 text-text-dim line-clamp-2">{m.blurb}</p>
        <div className="font-mono text-10 text-text-mute">
          {m.paramCount} {m.paramCount === 1 ? "param" : "params"}
        </div>
      </div>
    </Link>
  );
}

function groupByCategory(models: ModelEntry[]): Map<string, ModelEntry[]> {
  const grouped = new Map<string, ModelEntry[]>();
  for (const m of models) {
    const list = grouped.get(m.categoryId) ?? [];
    list.push(m);
    grouped.set(m.categoryId, list);
  }
  return grouped;
}
