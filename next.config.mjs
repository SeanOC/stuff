/** @type {import('next').NextConfig} */
const nextConfig = {
  // Don't try to bundle openscad-wasm-prebuilt's giant inline-base64
  // WASM into the server bundle — leave it as an external CommonJS
  // require at runtime. The package targets browser ESM and Node;
  // letting webpack/turbopack inline it triggers a 10MB+ string
  // serialization that has caused OOM on Vercel builds in the past.
  serverExternalPackages: ["openscad-wasm-prebuilt"],

  // The API routes read from models/, libs/, and renders/ via
  // `process.cwd()` at request time. Next.js file-tracing can't see
  // those dynamic reads, so without explicit includes nothing ships
  // with the function bundle and every request 500s on Vercel.
  outputFileTracingIncludes: {
    "/api/source": ["./libs/**/*.scad", "./models/**/*.scad"],
    "/api/export": ["./libs/**/*.scad", "./models/**/*.scad"],
    // SCAD thumbnails live under renders/; build123d thumbnails are
    // baked into build123d/baked/ by the prebuild bake (pst-1vi5), the
    // same artifact stream the GLB/STL come from. Both are dynamic
    // process.cwd() reads the tracer can't see, so include both.
    "/api/thumbnail": [
      "./renders/**/*.png",
      "./build123d/baked/**/*.png",
      "./build123d/manifest.json",
    ],
    // Accessory STL streamer + the model page that lists them — both
    // stat / read files under accessories/ via process.cwd() at request
    // time, so the file tracer needs the include hint.
    "/api/accessories/[slug]": ["./accessories/**/*.stl"],
    // The detail page reads accessories/ (SCAD) AND, for build123d
    // models, the committed manifest.json (loadBdModel, at request time).
    "/models/[slug]": ["./accessories/**/*.stl", "./build123d/manifest.json"],
    // build123d baked-preset server (pst-0um9). The prebuild bake writes
    // build123d/baked/; the tracer can't see the runtime fs reads, so the
    // route's files are listed here, plus the manifest for the allowlist
    // check. ONLY the viewer GLBs ship (pst-acoed): Vercel packs these
    // routes into one function, and the baked STL/3MF/per-colour STLs
    // took it to 345 MB (limit 250). The preset STL/3MF are published to
    // Vercel Blob by the bake instead (pst-scmib), and the route finds them
    // through blob-record.json — which must ship, or every download 404s.
    // Budget guard: scripts/function-bundle-budget.test.ts.
    "/api/bd-asset/[slug]/[preset]": [
      "./build123d/baked/**/*.glb",
      "./build123d/baked/blob-record.json",
      "./build123d/manifest.json",
    ],
  },

  // Routes that resolve a path from process.cwd() plus a runtime value
  // (accessories' entry.stlPath, export/source's model path) make the
  // tracer pull in most of the repo, so each of those functions shipped
  // all of build123d/baked/ and build123d/tests/: "api/accessories/[slug]"
  // reached 345 MB against Vercel's 250 MB limit once the tombstone-sign
  // presets were baked (pst-acoed). Drop, from EVERY function, the files
  // no route reads at runtime: the baked STL/3MF/per-colour STLs
  // (/api/bd-asset streams the preset STL/3MF from Vercel Blob) and the
  // build123d dev trees. Budget guard: scripts/function-bundle-budget.test.ts.
  outputFileTracingExcludes: {
    "/**": [
      "./build123d/baked/**/*.stl",
      "./build123d/baked/**/*.3mf",
      "./build123d/tests/**/*",
      "./build123d/docs/**/*",
      "./build123d/out/**/*",
    ],
  },
};

export default nextConfig;
