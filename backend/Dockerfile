FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies (cached layer)
COPY pyproject.toml ./
RUN mkdir -p app && echo '__version__ = "0.1.0"' > app/__init__.py && \
    uv pip install --system ".[dev]" && \
    rm app/__init__.py

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
