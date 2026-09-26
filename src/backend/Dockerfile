FROM python:3.13.2-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.6.5 /uv /uvx /bin/
COPY src/backend/pyproject.toml src/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/backend/alembic.ini ./alembic.ini
COPY src/backend/alembic ./alembic
COPY src/backend/app ./app
COPY src/backend/entrypoint.sh ./entrypoint.sh
COPY fixtures.json ./fixtures.json

EXPOSE 8000
CMD ["sh", "/app/entrypoint.sh"]
