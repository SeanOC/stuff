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
    "/api/thumbnail": ["./renders/**/*.png"],
    // Accessory STL streamer + the model page that lists them — both
    // stat / read files under accessories/ via process.cwd() at request
    // time, so the file tracer needs the include hint.
    "/api/accessories/[slug]": ["./accessories/**/*.stl"],
    // The detail page reads accessories/ (SCAD) AND, for build123d
    // models, the committed manifest.json (loadBdModel, at request time).
    "/models/[slug]": ["./accessories/**/*.stl", "./build123d/manifest.json"],
    // build123d baked-preset server (pst-0um9). The STL/GLB are baked
    // into build123d/baked/ by the prebuild bake step; the tracer can't
    // see the runtime fs reads, so include the whole baked tree in the
    // route's function bundle, plus the manifest for the allowlist check.
    "/api/bd-asset/[slug]/[preset]": [
      "./build123d/baked/**/*",
      "./build123d/manifest.json",
    ],
  },
};

export default nextConfig;
