# Stage 1: Node 26 builder for frontend static assets
FROM node:26-slim AS frontend-builder

WORKDIR /app/web

COPY web/package*.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


# Stage 2: Python 3.14 runtime
FROM python:3.14-slim AS backend-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:/root/.local/bin:$PATH"

# Deps layer: third-party + extras only, no project needed.
# Cached against pyproject/uv.lock, so src/ edits don't re-resolve deps.
RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    uv sync --all-extras --no-install-project

COPY src/ ./src/
COPY web/genreguru_web/ ./web/genreguru_web/
COPY web/manage.py ./web/
COPY config/ ./config/

COPY --from=frontend-builder /app/web/fingerprint_app/static/fingerprint_app/ ./web/fingerprint_app/static/fingerprint_app/

# Project layer: after COPY src/; installs genreguru itself (uv_build).
# LICENSE bind-mount supplies wheel metadata (license-files glob).
RUN --mount=from=ghcr.io/astral-sh/uv:latest,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    uv sync --all-extras --compile-bytecode

ENV PYTHONPATH=/app/src:/app/web
ENV GENREGURU_ENV=prod
ENV DJANGO_SETTINGS_MODULE=genreguru_web.settings.production

COPY config/docker/entrypoint.sh /app/config/docker/entrypoint.sh
RUN chmod +x /app/config/docker/entrypoint.sh

ENTRYPOINT ["/app/config/docker/entrypoint.sh"]
