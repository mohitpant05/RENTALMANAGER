FROM python:3.12-slim AS base

WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Development target
FROM base AS dev
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system ".[dev]" && \
    rm app/__init__.py
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production target
FROM base AS prod
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system . && \
    rm app/__init__.py
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]