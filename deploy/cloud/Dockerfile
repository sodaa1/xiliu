# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS web
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
COPY docs/web/scripts/config.mjs /build/docs/web/scripts/config.mjs
RUN npm run build:cloud && npm run build:guest

FROM ghcr.io/astral-sh/uv:0.9.3 AS uv
FROM python:3.12-slim-bookworm AS python
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev --no-editable
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN .venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base'); tiktoken.get_encoding('o200k_base')"

FROM debian:bookworm-slim AS egress
RUN apt-get update && apt-get install -y --no-install-recommends iptables \
    && rm -rf /var/lib/apt/lists/*
COPY deploy/cloud/egress.sh /usr/local/bin/egress.sh
CMD ["sh", "/usr/local/bin/egress.sh"]

FROM python:3.12-slim-bookworm AS app
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    XILIU_CLOUD_DATA_DIR=/data XILIU_CLOUD_STATIC_DIR=/app/web/dist \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache HOME=/tmp
WORKDIR /app
RUN mkdir /data && chown 10001:10001 /data
COPY --from=python /build/.venv /app/.venv
COPY --from=python /opt/tiktoken-cache /opt/tiktoken-cache
COPY --from=web /build/web/dist-cloud /app/web/dist
COPY --from=web /build/web/dist-guest /app/web/dist/demo
USER 10001:10001
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "xiliu.cloud.app:create_cloud_app", "--factory", "--host", "0.0.0.0", "--port", "8765", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
