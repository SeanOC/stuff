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
  },
};

export default nextConfig;
