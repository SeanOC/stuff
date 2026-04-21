import Link from "next/link";
import { listModels } from "@/lib/models/discover";

export default async function Home() {
  const models = await listModels();

  return (
    <main style={{ padding: "2rem", maxWidth: 1200, margin: "0 auto" }}>
      <h1 style={{ marginTop: 0 }}>stuff — parametric models</h1>
      <p style={{ color: "#8b949e", marginTop: 0 }}>
        {models.length} {models.length === 1 ? "model" : "models"}. Open one to
        tune params and download the STL.
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: "1rem",
          marginTop: "1.5rem",
        }}
      >
        {models.map((m) => (
          <Link
            key={m.slug}
            href={`/models/${m.slug}`}
            style={{
              display: "flex",
              flexDirection: "column",
              background: "#0d1117",
              border: "1px solid #30363d",
              borderRadius: 6,
              overflow: "hidden",
              textDecoration: "none",
              color: "inherit",
              transition: "border-color 120ms",
            }}
          >
            <div
              style={{
                aspectRatio: "4 / 3",
                background: `#161b22 url("/api/thumbnail?model=${encodeURIComponent(m.slug)}") center / cover no-repeat`,
                borderBottom: "1px solid #30363d",
              }}
              aria-label={`top view of ${m.title}`}
            />
            <div style={{ padding: "0.75rem 0.9rem" }}>
              <div style={{ fontWeight: 600, color: "#e6edf3" }}>{m.title}</div>
              <div
                style={{
                  marginTop: "0.2rem",
                  fontSize: "0.8rem",
                  color: m.annotated ? "#8b949e" : "#d29922",
                }}
              >
                {m.annotated
                  ? `${m.paramCount} parameter${m.paramCount === 1 ? "" : "s"}`
                  : "not yet annotated"}
              </div>
              <code
                style={{
                  display: "block",
                  marginTop: "0.35rem",
                  fontSize: "0.72rem",
                  color: "#6e7681",
                }}
              >
                {m.stem}.scad
              </code>
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
