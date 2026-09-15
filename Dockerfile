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

RUN curl --proto '=https' --tlsv1.2 -sSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock ./
RUN uv sync --all-extras --dev

COPY src/ ./src/
COPY web/genreguru_web/ ./web/genreguru_web/
COPY web/manage.py ./web/
COPY config/ ./config/

COPY --from=frontend-builder /app/web/fingerprint_app/static/fingerprint_app/ ./web/fingerprint_app/static/fingerprint_app/

ENV PYTHONPATH=/app/src:/app/web
ENV GENREGURU_ENV=prod
ENV DJANGO_SETTINGS_MODULE=genreguru_web.settings.production

COPY config/docker/entrypoint.sh /app/config/docker/entrypoint.sh
RUN chmod +x /app/config/docker/entrypoint.sh

ENTRYPOINT ["/app/config/docker/entrypoint.sh"]
