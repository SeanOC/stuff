/** @type {import('next').NextConfig} */
const nextConfig = {
  // Don't try to bundle openscad-wasm-prebuilt's giant inline-base64
  // WASM into the server bundle — leave it as an external CommonJS
  // require at runtime. The package targets browser ESM and Node;
  // letting webpack/turbopack inline it triggers a 10MB+ string
  // serialization that has caused OOM on Vercel builds in the past.
  serverExternalPackages: ["openscad-wasm-prebuilt"],
};

export default nextConfig;
