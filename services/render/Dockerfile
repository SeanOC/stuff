# Native OpenSCAD render service — Phase 1 spike (st-065, plan st-rtb).
#
# Wraps a headless native `openscad -o out.stl -D <defines> <model>`
# behind POST /render. Models AND libraries are BAKED into the image and
# the openscad version is PINNED, so a render is a pure function of
# (model, params) with no network and no per-request asset fetch.
#
# Base pin: openscad/openscad:dev.2025-09-06 — the SAME image CI renders
# with (.github/workflows/ci.yml), so the service's output tracks the
# reference STLs the invariants are written against. Bumping this tag is
# a deliberate, cache-busting change (it can move geometry).

# ---- build stage: bundle the TS service to one dependency-free ESM ----
# Bundling the actual lib/scad-params/parse.ts (not a copy) is what
# guarantees param->define parity with the app/WASM path.
FROM node:22-slim AS build
WORKDIR /build
# esbuild pinned to the repo's version so the bundler is reproducible.
RUN npm install --no-save --no-audit --no-fund esbuild@0.21.5
COPY lib/scad-params ./lib/scad-params
COPY services/render/server.ts services/render/render.ts services/render/build.mjs ./services/render/
RUN node services/render/build.mjs

# ---- runtime stage: openscad + node + baked models/libs ----
FROM openscad/openscad:dev.2025-09-06

# node (to run the bundle), git + ca-certificates (to vendor libs at
# build), xvfb as insurance for openscad builds that want a display.
# The openscad/openscad image is Debian-based but minimal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nodejs ca-certificates git xvfb xauth \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Vendor the pinned libraries (BOSL2, QuackWorks, gridfinity) into
# /app/libs at the SHAs in libs/README.md. Needs network at build only.
COPY scripts/vendor-libs.sh ./scripts/vendor-libs.sh
COPY libs/README.md ./libs/README.md
RUN bash scripts/vendor-libs.sh

# Bake every model (+ its invariants sidecar + any import() asset).
COPY models/ ./models/

# One intentional-failure fixture so the failure path (openscad ERROR →
# 500 {ok:false}, never an STL) can be exercised against the container.
COPY tests/fixtures/render_service_bad.scad ./tests/fixtures/render_service_bad.scad

# The bundled service.
COPY --from=build /build/services/render/dist/server.mjs ./server.mjs

# Fixed absolute model path + pinned engine => byte-reproducible renders.
# OpenSCAD's STL tessellation is sensitive to the model's absolute path,
# so this mount point must stay stable across deploys (st-065 finding).
ENV RENDER_REPO_ROOT=/app \
    OPENSCADPATH=/app/libs \
    PORT=8080 \
    RENDER_XVFB=0

EXPOSE 8080
CMD ["node", "/app/server.mjs"]
