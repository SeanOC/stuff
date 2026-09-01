# Live build123d render service (bead pst-so26) — Cloud Run image.
#
# The build123d analogue of services/render/Dockerfile. Where that bakes
# OpenSCAD + models/, this bakes the build123d/OCP env (via uv, pinned by
# build123d/uv.lock) plus the holders package (registry + models), so a
# render is a pure function of (slug, params) with no per-request network.
#
# Build context is the REPO ROOT (matches deploy-bd-render-service.yml):
#   docker build -f services/bd-render/Dockerfile -t stuff-bd-render .
#
# Env is pinned by build123d/uv.lock (uv sync --frozen); bumping OCP or
# opengrid is a deliberate, cache-busting lockfile change that can move
# geometry — redeploy in lockstep with the app's baked presets.

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# OCP (cadquery-ocp) pulls in Open CASCADE, which links a handful of X/GL
# shared libs even for headless meshing; git + CA certs let uv fetch the
# opengrid git source pinned in pyproject.toml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git ca-certificates \
        libgl1 libglu1-mesa libxrender1 libxext6 libsm6 libx11-6 \
        libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build123d

# Dependency layer first (cached until the lockfile changes). --frozen
# forbids any lock mutation; --no-install-project because there is no
# importable project package — holders/ is imported via BD_BUILD123D_ROOT
# on sys.path, exactly as the worker does.
ENV UV_LINK_MODE=copy
COPY build123d/pyproject.toml build123d/uv.lock ./
RUN uv sync --frozen --no-install-project

# Bake the model tree: registry + holders (models) + export helpers.
COPY build123d/holders ./holders
COPY build123d/scripts ./scripts

# The service (server + one-shot render worker).
COPY services/bd-render/server.py services/bd-render/render_worker.py /services/bd-render/

# Fixed absolute build123d root => registry/holders import the same way in
# the container as under test. Run the server on the uv-synced interpreter
# directly (its sys.executable is what the worker subprocess inherits, so
# the worker gets the same OCP env).
ENV BD_BUILD123D_ROOT=/build123d \
    PORT=8080 \
    BD_RENDER_TIMEOUT=90

EXPOSE 8080
CMD ["/build123d/.venv/bin/python", "/services/bd-render/server.py"]
