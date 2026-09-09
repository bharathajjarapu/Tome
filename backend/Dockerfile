# One image for the API and the worker; compose picks the command.
FROM docker.io/library/python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    FASTEMBED_CACHE_PATH=/models
WORKDIR /app

# Dependencies first, so a code change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY alembic alembic
COPY tome tome
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 1000 tome \
    && mkdir -p /data/uploads /models \
    && chown tome /data/uploads /models
USER tome

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn tome.main:app --host 0.0.0.0 --port 8000"]
