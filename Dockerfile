# ============================================================
# Stage 1: ビルドステージ - 依存関係のインストール
# ============================================================
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# ============================================================
# Stage 2: 実行ステージ
# ============================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# 仮想環境コピー
COPY --from=builder /build/.venv /app/.venv

# アプリコードコピー(実行時にimportするため必要)
COPY --from=builder /build/app /app/app
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
