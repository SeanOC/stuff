import Link from "next/link";
import { listModels } from "@/lib/models/discover";

export default async function Home() {
  const models = await listModels();

  return (
    <div className="px-24 py-24">
      <h1 className="m-0 text-22 font-semibold">stuff — parametric models</h1>
      <p className="mt-6 mb-24 text-12 text-text-dim">
        {models.length} {models.length === 1 ? "model" : "models"}. Open one to
        tune params and download the STL.
      </p>
      <div
        className="grid gap-14"
        style={{ gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}
      >
        {models.map((m) => (
          <Link
            key={m.slug}
            href={`/models/${m.slug}`}
            className="flex flex-col overflow-hidden rounded-4 border border-line bg-panel no-underline text-text transition-colors hover:border-accent-line hover:bg-panel-hi"
          >
            <div
              className="border-b border-line-soft"
              style={{
                aspectRatio: "4 / 3",
                background: `var(--color-panel2) url("/api/thumbnail?model=${encodeURIComponent(m.slug)}") center / cover no-repeat`,
              }}
              aria-label={`top view of ${m.title}`}
            />
            <div className="p-12">
              <div className="font-semibold text-13 text-text">{m.title}</div>
              <div
                className={`mt-3 text-11 ${m.annotated ? "text-text-dim" : "text-warn"}`}
              >
                {m.annotated
                  ? `${m.paramCount} parameter${m.paramCount === 1 ? "" : "s"}`
                  : "not yet annotated"}
              </div>
              <code className="mt-4 block font-mono text-10 text-text-mute">
                {m.stem}.scad
              </code>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
